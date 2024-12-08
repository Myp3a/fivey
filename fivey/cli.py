import os
from typing import Any, Callable, Literal

from fivey.stores import Store
from fivey.client import Client
from fivey.orders import Card, Order
from fivey.catalog import Item, Category, Subcategory

from fivey.location import location_by_search


def draw_auth_menu() -> str:
    lines = "1. Авторизоваться по номеру\n" "2. Подставить токен\n" "3. Выход\n" "\n"
    return lines


def draw_header(address: str, price: str) -> str:
    cols, _ = os.get_terminal_size()
    free_space = cols - len(address) - len(price) - 8
    if free_space < 1:
        address = address[: cols - len(price) - 16] + "... "
        free_space = cols - len(address) - len(price) - 8
    return left_right(address, price)


def draw_main_menu() -> str:
    lines = (
        "1. Каталог\n"
        "2. Поиск\n"
        "3. Корзина\n"
        "4. Заказать\n"
        "9. Мои заказы\n"
        "0. Сменить адрес\n"
        "q. Выход\n"
    )
    return lines


def draw_entire_screen(header: str, lines: str) -> None:
    cols, _ = os.get_terminal_size()
    cols -= 4
    out = [
        f"+{"-"*(cols-2)}+\n",
        f"| {header} |\n",
        f"+{"-"*(cols-2)}+\n",
    ]
    out.extend(
        [
            f"| {f"{r}{" "*(cols-len(r)-4)}" if len(r) < cols-3 else f"{r[:cols-7]}..."} |\n"
            for r in lines.split("\n")
        ]
    )
    out.append(f"+{"-"*(cols-2)}+\n")
    print("".join(out), end="", flush=True)


def left_right(left: str, right: str) -> str:
    cols, _ = os.get_terminal_size()
    cols -= 4
    free_space = cols - len(left) - len(str(right)) - 4
    if free_space < 1:
        left = left[: cols - len(str(right)) - 12] + "... "
        free_space = cols - len(left) - len(str(right)) - 4
    return f"{left}{" " * (free_space)}{right}"


def paginate(
    order: Order,
    store: Store,
    items: list[Item | Category | Subcategory | Store | Card],
    action: Callable,
    action_type: Literal["select", "remove", "get_value", "set_store"],
) -> Any:
    page = 0
    pages: list[list[Item | Category | Subcategory | Store | Card]] = [[]]
    indexes = "1234567890"
    for i in items:
        if len(pages[page]) > 9:
            page += 1
            pages.append([])
        pages[page].append(i)
    page = 0
    while True:
        assert order.address
        header = draw_header(
            f"{order.address.house}, {order.address.street}, {order.address.city} (Пятерочка {store.sap_code})",
            f"{order.order_sum} руб. (+ {order.service_sum} руб.)",
        )
        if not pages[page]:
            lines = ["Ничего!\n"]
        elif isinstance(pages[page][0], Item):
            lines = [
                f"{
                left_right(
                    f"{indexes[i]}. {pages[page][i].name} x{pages[page][i].quantity}",  # type: ignore
                    f"{pages[page][i].price} / {pages[page][i].uom}"  # type: ignore
                )}\n"
                for i in range(len(pages[page]))
            ]
        elif isinstance(pages[page][0], Category) or isinstance(
            pages[page][0], Subcategory
        ):
            lines = [
                f"{indexes[i]}. {pages[page][i].name}\n"  # type: ignore
                for i in range(len(pages[page]))
            ]
        elif isinstance(pages[page][0], Store):
            lines = [
                f"{
                left_right(
                    f"{indexes[i]}. {pages[page][i].shop_address}",  # type: ignore
                    f"({pages[page][i].sap_code})"  # type: ignore
                )}\n"
                for i in range(len(pages[page]))
            ]
        elif isinstance(pages[page][0], Card):
            lines = [
                f"{indexes[i]}. {pages[page][i].number}\n"  # type: ignore
                for i in range(len(pages[page]))
            ]
        lines.append("\n")
        allowed_choices = indexes[: len(pages[page])] + "bq"
        if page < len(pages) - 1:
            lines.append("n. Следующая страница\n")
            allowed_choices += "n"
        if page > 0:
            lines.append("p. Предыдущая страница\n")
            allowed_choices += "p"
        lines.append("b. Назад\n")
        line = "".join(lines)
        draw_entire_screen(header, line)
        got_input = False
        while not got_input:
            letter = input("Выбор: ")
            if len(letter) == 1 and letter in allowed_choices:
                got_input = True
        match letter:
            case "n":
                page += 1
            case "p":
                page -= 1
            case "b":
                return
            case "q":
                quit()
            case _:
                if action_type == "remove":
                    pages[page].pop(indexes.index(letter))
                    order = action(pages[page][indexes.index(letter)])
                if action_type == "select":
                    order = action(pages[page][indexes.index(letter)])
                if action_type == "get_value":
                    return pages[page][indexes.index(letter)]
                if action_type == "set_store":
                    return action(pages[page][indexes.index(letter)])


def main():
    cli = Client()
    if not cli.auth.load_token_from_file():
        header = draw_header("Неизвестно", 0.0)
        auth = draw_auth_menu()
        draw_entire_screen(header, auth)
        got_input = False
        while not got_input:
            letter = input("Выбор: ")
            if len(letter) == 1 and letter in "123q":
                got_input = True
        match letter:
            case "1":
                got_input = False
                phone = ""
                while not got_input:
                    phone = input("Телефон: +7")
                    if len(phone) == 10:
                        got_input = True
                cli.auth.cli_auth(phone)
            case "2":
                token = input("Вставьте токен: ")
                cli.auth.set_token(token, "")
            case "3" | "q":
                quit()
    if not cli.auth.check_auth(cli.token):
        print("Авторизация не удалась!")
        quit()
    prev_order = cli.orders.orders()[0]
    prev_addr = prev_order.address
    addr_string = f"{prev_addr.house}, {prev_addr.street}, {prev_addr.city}"
    addr = location_by_search(addr_string)
    my_store = cli.stores.store_by_location(addr["lat"], addr["lon"])
    cli.stores.set_current_store(my_store)
    cli.orders.create_order(
        addr["house"], addr["street"], addr["city"], addr["lat"], addr["lon"]
    )
    while True:
        curr_order = cli.order
        header = draw_header(
            f"{curr_order.address.house}, {curr_order.address.street}, {curr_order.address.city} (Пятерочка {cli.store.sap_code})",
            f"{curr_order.order_sum} руб. (+ {curr_order.service_sum} руб.)",
        )
        menu = draw_main_menu()
        draw_entire_screen(header, menu)
        got_input = False
        while not got_input:
            letter = input("Выбор: ")
            if len(letter) == 1 and letter in "123490q":
                got_input = True
                match letter:
                    case "1":
                        categories = cli.catalog.categories()
                        sel_cat = paginate(
                            curr_order,
                            cli.store,
                            categories,
                            lambda x: None,
                            action_type="get_value",
                        )
                        if sel_cat:
                            sel_subcat = paginate(
                                curr_order,
                                cli.store,
                                sel_cat.subcategories,
                                lambda x: None,
                                action_type="get_value",
                            )
                            if sel_subcat:
                                items = cli.catalog.products_list(sel_subcat.id)
                                paginate(
                                    curr_order,
                                    cli.store,
                                    items,
                                    cli.basket.put,
                                    action_type="select",
                                )
                    case "2":
                        query = input("Искать: ")
                        items = cli.catalog.search(query)
                        paginate(
                            curr_order,
                            cli.store,
                            items,
                            cli.basket.put,
                            action_type="select",
                        )
                    case "3":
                        items = cli.order.basket
                        paginate(
                            curr_order,
                            cli.store,
                            items,
                            cli.basket.remove,
                            action_type="remove",
                        )
                    case "4":
                        flat = input("Квартира: ")
                        comment = input("Комментарий: ")
                        cli.orders.set_address_details("", flat, "", comment)
                        cli.orders.revise()
                        card = paginate(
                            curr_order,
                            cli.store,
                            cli.orders.get_payment_methods(),
                            lambda x: None,
                            "get_value",
                        )
                        cli.orders.pay(card)
                        cli.orders.create_order(
                            addr["house"],
                            addr["street"],
                            addr["city"],
                            addr["lat"],
                            addr["lon"],
                        )
                    case "9":
                        orders = cli.orders.orders(limit=10)
                        lines = [
                            left_right(
                                f"{o.human_id}: {o.address.house}, {o.address.street}, {o.address.city} ({o.total_sum} руб)",
                                f"{o.status}\n",
                            )
                            for o in orders
                        ]
                        lines.append("c. Отменить\n")
                        lines.append("b. Назад\n")
                        draw_entire_screen(header, "".join(lines))
                        got_input = False
                        while not got_input:
                            inp = input("Выбор: ")
                            if inp == "b":
                                got_input = True
                            elif inp == "c":
                                num = input("Номер заказа для отмены: ")
                                order = next(
                                    (o for o in orders if o.human_id == int(num)), None
                                )
                                if order:
                                    got_input = True
                                    cli.orders.cancel(order)
                    case "0":
                        query = input("Введите произвольный адрес: ")
                        addr = location_by_search(query)
                        my_store = cli.stores.store_by_location(
                            addr["lat"], addr["lon"]
                        )
                        if my_store.sap_code is None:
                            print("Не удалось найти Пятерочку по этому адресу!")
                            quit()
                        cli.stores.set_current_store(my_store)
                        curr_order = cli.orders.create_order(
                            addr["house"],
                            addr["street"],
                            addr["city"],
                            addr["lat"],
                            addr["lon"],
                        )
                    case "q":
                        quit()


main()
