from django.db import models
from django.utils.text import slugify



class Category(models.Model):
    TYPE_CHOICES = (
        ("mobiles", "Mobiles"),
        ("audio", "Audio"),
    )

    category_name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.category_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.category_name


class Brand(models.Model):
    brand_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.brand_name


class Product(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
    )

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="products")
    product_name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    short_description = models.TextField(blank=True)
    full_description = models.TextField(blank=True)
    product_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="active")
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_stock(self):
        return sum(v.stock_quantity for v in self.variants.filter(is_active=True))

    @property
    def active_variant_count(self):
        return self.variants.filter(is_active=True).count()
    
    @property
    def default_variant(self):
        return self.variants.filter(is_default=True, is_active=True).first()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.product_name)
        super().save(*args, **kwargs)


 

    def __str__(self):
        return self.product_name


class ProductSpecification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="specifications")
    spec_name = models.CharField(max_length=100)
    spec_value = models.CharField(max_length=255)

    def __str__(self):
        return self.spec_name


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    color = models.CharField(max_length=50)
    ram = models.CharField(max_length=50, blank=True, null=True)
    storage = models.CharField(max_length=50, blank=True, null=True)
    connectivity = models.CharField(max_length=50, blank=True, null=True)
    battery_life = models.CharField(max_length=50, blank=True, null=True)
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_quantity = models.PositiveIntegerField(default=0)
    main_image = models.ImageField(upload_to="products/variants/main/", blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.sku
    
    


class VariantImage(models.Model):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/variants/gallery/")

    def __str__(self):
        return self.variant.sku
