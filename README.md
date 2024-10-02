# Пятерочка Доставка API
API для заказа доставки из Пятерочки с CLI-интерфейсом. А почему бы и нет?

# Установка
```
pip install fivey
```

# Использование
Доступно использование в интерактивном режиме через:
```
fivey
```
> Не проверено на новом аккаунте, без единого заказа

ИЛИ

```Python
from fivey import Client
cli = Client()
cli.auth.interactive_auth(phone_without_+7)
print(cli.orders.orders())
```
