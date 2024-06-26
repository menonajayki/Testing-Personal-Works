from django.db import models
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from users.models import User
from octorest import OctoRest


class Supplier(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=120, unique=True)
    address = models.CharField(max_length=220)
    created_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.name


class Buyer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=120, unique=True)
    address = models.CharField(max_length=220)
    created_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=120, unique=True)
    sortno = models.PositiveIntegerField()
    created_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICE = (
        ('pending', 'Pending'),
        ('decline', 'Decline'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('complete', 'Complete'),
        ('delivered', 'Delivered'),
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    design = models.CharField(max_length=50)
    color = models.CharField(max_length=50)
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICE)
    created_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.product.name

    # Octoprint Integration -- also done at admin, make this modular
    def save(self, *args, **kwargs):
        created = not self.pk
        super().save(*args, **kwargs)
        if created and self.status == 'approved':
            self.print_order()


    def print_order(self):
        octo_url = "http://octopi.local/"
        octo_apikey = "3342ACFDFCF0460AA0BF4E148A125F3B"
        client = OctoRest(url=octo_url, apikey=octo_apikey)

        file_path = "red.gcode"
        print("Initiating print job...")
        client.select(file_path)
        client.start()
        print("Print job started successfully!")

class Delivery(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    courier_name = models.CharField(max_length=120)
    created_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.courier_name

    def save(self, *args, **kwargs):
        created = not self.pk
        super().save(*args, **kwargs)
        if created:
            # Send WebSocket message after saving
            self.send_delivery_message()

    def send_delivery_message(self):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'orders',
            {
                'type': 'delivery_message',
                'message': {
                    'order_id': self.order.id,
                    'courier_name': self.courier_name,
                    'status': 'Delivered',
                    'message': f"Delivery for Order {self.order.id} has been completed."
                }
            }
        )
