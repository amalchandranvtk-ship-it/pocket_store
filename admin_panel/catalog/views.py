from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Sum,Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.text import slugify
from django.views.decorators.cache import never_cache
import base64 
from django.core.files.base import ContentFile
import re

from .models import (Category, Brand,Product,ProductSpecification, ProductVariant, VariantImage)


def is_admin(user):
    return user.is_authenticated and user.is_staff


def admin_name(request):
    return request.user.full_name or request.user.first_name or request.user.username


def valid_decimal(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        return None


def validate_category(name, type_value,description):
    if not name:
        return "Category is required"
    if not name.replace(" ","").isalpha():
        return "Category name must contain only letters"
    if len(name.strip())<3:
        return "Category name must contain atleast 3 characters"
    if not type_value:
        return "Category type is required"
    if type_value not in ["mobiles", "audio"]:
        return "Invalid category type"
    if not description:
        return "Description is required"
    if len(description.strip())<5:
        return "Description must contain atleast 5 characters"
    return None




def validate_product(name, category_id, brand_id,short_description,full_description, edit=False):
    name = name.strip()
    short_description=short_description.strip()
    full_description=full_description.strip()
    if not name:
        return "Product name is required"

    if len(name) < 3:
        return "Product name must contain at least 3 characters"

    if not re.match(r'^[A-Za-z0-9 ]+$', name):
        return "Product name can contain only letters, numbers and spaces"

    if not category_id:
        return "Category is required"

    if not brand_id:
        return "Brand is required"
    if not short_description:
        return "Short description is required"
    if len(short_description)<8:
        return "Short description must contain atleast 8 characters"
   

    if not full_description:
        return "Full description is required"
    if len(full_description)<8:
        return "Full description must contain atleast 8 characters"
    
    return None

def validate_image_file(image):
    allowed_extensions= ["jpg","jpeg","png","webp"]
    ext=image.name.split(".")[-1].lower()
    if ext not in allowed_extensions:
        return "Only jpg, jpeg, png, webp images are allowed"
    if image.size> 5 * 1024 * 1024:
        return "Image size must be below 5MB"
    
    return None

def validate_variant(product, color, sku, price, stock, ram="", storage="", connectivity="", battery_life="", variant_id=None):
    if not color:
        return "Color is required"
    if not color.replace(" ","").isalpha():
        return "color must contain letters"
    if len(color)<2:
        return "color must contain atleast 2 characters"
    if not sku:
        return "SKU is required"
    if len(sku)<2:
        return "sku must contain atleast 2 characters"

    sku_qs = ProductVariant.objects.filter(sku=sku)
    if variant_id:
        sku_qs = sku_qs.exclude(id=variant_id)

    if sku_qs.exists():
        return "SKU already exists"

    price_value = valid_decimal(price)
    if price_value is None or price_value <= 0:
        return "Enter valid price greater than 0"

    try:
        stock_value = int(stock)
        if stock_value < 0:
            return "Stock cannot be negative"
    except:
        return "Enter valid stock quantity"

    if product.category.type == "mobiles":
        if not ram:
            return "RAM is required for mobile variant"
        if not any(char.isdigit() for char in ram):
            return "RAM must contain at least one number"
        if not storage:
            return "Storage is required for mobile variant"
        if not any(char.isdigit() for char in storage):
            return "Storage must contain at least one number"

 
    if product.category.type == "audio":
        if not connectivity:
            return "Connectivity is required for audio variant"
        if not connectivity.replace(" ","").isalpha():
            return "Connectivity must contain letters"
        if not battery_life:
            return "Battery life is required for audio variant"
        if not any(char.isdigit() for char in battery_life):
            return "Battery life must contain at least one number"
        

    return None


@never_cache
@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def category_list(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    type_filter = request.GET.get("type", "").strip()

    categories = Category.objects.filter(is_deleted=False).annotate(
        total_stock=Sum(
            'products__variants__stock_quantity',
            filter=Q(
                products__is_deleted=False,
                products__variants__is_active=True,
                products__product_status="active"

            ))).order_by("-id")

    if q:
        categories = categories.filter(
            Q(category_name__icontains=q) |
            Q(slug__icontains=q)
        )

    if status == "active":
        categories = categories.filter(is_active=True)
    elif status == "inactive":
        categories = categories.filter(is_active=False)

    if type_filter:
        categories = categories.filter(type=type_filter)

    paginator = Paginator(categories, 5)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "catalog/category_list.html", {
        "categories": page_obj,
        "page_obj": page_obj,
        "q": q,
        "status": status,
        "type_filter": type_filter,
        "admin_name": admin_name(request),
    })


@never_cache
@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def category_form(request, category_id=None):
    category = None
    title = "Add New Category"

    if category_id:
        category = get_object_or_404(Category, id=category_id, is_deleted=False)
        title = "Edit Category"

    if request.method == "POST":
        name = request.POST.get("category_name", "").strip()
        type_value = request.POST.get("type", "").strip()
        description = request.POST.get("description", "").strip()
        image = request.FILES.get("image")
        is_active = True if request.POST.get("is_active") else False

        error = validate_category(name, type_value,description)
        if error:
            messages.error(request, error)
            return redirect(request.path)
        if image:
            error=validate_image_file(image)
            if error:
                messages.error(request,error)
                return redirect(request.path)

        exists = Category.objects.filter(category_name__iexact=name, is_deleted=False)
        if category:
            exists = exists.exclude(id=category.id)

        if exists.exists():
            messages.error(request, "Category already exists")
            return redirect(request.path)

        if category is None:
            category = Category()

        category.category_name = name
        category.slug = slugify(name)
        category.type = type_value
        category.description = description
        category.is_active = is_active

        if image:
            category.image = image

        category.save()
        messages.success(request, "Category saved successfully")
        return redirect("category_list")

    return render(request, "catalog/category_form.html", {
        "category": category,
        "title": title,
        "admin_name": admin_name(request),
    })


@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.is_deleted = True
    category.is_active = False
    category.save()

    messages.success(request, "Category deleted successfully")
    return redirect("category_list")


@never_cache
@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def product_list(request):
    q = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()
    brand_id = request.GET.get("brand", "").strip()
    stock = request.GET.get("stock", "").strip()

    products = Product.objects.filter(is_deleted=False).select_related("category", "brand").order_by("-id")

    if q:
        products = products.filter(
            Q(product_name__icontains=q) |
            Q(slug__icontains=q) |
            Q(variants__sku__icontains=q)
        ).distinct()

    if category_id:
        products = products.filter(category_id=category_id)

    if brand_id:
        products = products.filter(brand_id=brand_id)

    products = list(products)

    if stock == "in_stock":
        products = [p for p in products if p.total_stock > 10]
    elif stock == "low_stock":
        products = [p for p in products if 1 <= p.total_stock <= 10]
    elif stock == "out_of_stock":
        products = [p for p in products if p.total_stock == 0]

    paginator = Paginator(products, 5)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "catalog/product_list.html", {
        "products": page_obj,
        "page_obj": page_obj,
        "categories": Category.objects.filter(is_active=True, is_deleted=False),
        "brands": Brand.objects.filter(is_active=True),
        "q": q,
        "category_id": category_id,
        "brand_id": brand_id,
        "stock": stock,
        "admin_name": admin_name(request),
    })


@never_cache
@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def product_form(request, product_id=None):
    product = None
    title = "Add New Product"

    if product_id:
        product = get_object_or_404(Product, id=product_id, is_deleted=False)
        title = "Edit Product"

    if request.method == "POST":
        name = request.POST.get("product_name", "").strip()
        category_id = request.POST.get("category", "")
        brand_id = request.POST.get("brand", "")
        

        exists = Product.objects.filter(product_name__iexact=name, is_deleted=False)
        if product:
            exists = exists.exclude(id=product.id)

        if exists.exists():
            messages.error(request, "Product already exists")
            return redirect(request.path)

        if product is None:
            product = Product()

        product.product_name = name
        product.slug = slugify(name)
        product.category_id = category_id
        product.brand_id = brand_id
        product.short_description = request.POST.get("short_description", "")
        product.full_description = request.POST.get("full_description", "")
        product.product_status = request.POST.get("product_status", "active")
        error = validate_product(name, category_id, brand_id, product.short_description,product.full_description,edit=bool(product))
        if error:
            messages.error(request, error)
            return redirect(request.path)


        product.save()

        ProductSpecification.objects.filter(product=product).delete()

        spec_names = request.POST.getlist("spec_name")
        spec_values = request.POST.getlist("spec_value")
        for spec_name in spec_names:
            spec_name = spec_name.strip()

            if not spec_name:
                messages.error(request, "Specification name is required")
                return redirect(request.path)
            if not spec_name.replace(" ","").isalpha():
                messages.error(request,"Specification name must contain letters")
                return redirect(request.path)

        for spec_name, spec_value in zip(spec_names, spec_values):
            if spec_name and spec_value:
                ProductSpecification.objects.create(
                    product=product,
                    spec_name=spec_name,
                    spec_value=spec_value
                )

        messages.success(request, "Product saved successfully")

        if product.active_variant_count == 0:
            return redirect("add_variant", product_id=product.id)

        return redirect("product_list")

    return render(request, "catalog/product_form.html", {
        "product": product,
        "categories": Category.objects.filter(is_active=True, is_deleted=False),
        "brands": Brand.objects.filter(is_active=True),
        "title": title,
        "admin_name": admin_name(request),
    })


@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_deleted = True
    product.product_status = "inactive"
    product.save()

    messages.success(request, "Product deleted successfully")
    return redirect("product_list")


@never_cache
@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def variant_list(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_deleted=False)

    variants = product.variants.filter(is_deleted=False).order_by("-id")

    paginator = Paginator(variants, 5)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "catalog/variant_list.html", {
        "product": product,
        "variants": page_obj,
        "page_obj": page_obj,
        "admin_name": admin_name(request),
    })


@never_cache
@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def variant_form(request, product_id=None, variant_id=None):
    variant = None

    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id)
        product = variant.product
        title = "Edit Variant"
    else:
        product = get_object_or_404(Product, id=product_id, is_deleted=False)
        title = "Add Variant"
    wired_categories = ["Wired Earphones","Wired Headphones","AUX Speakers","Studio Headphones","Computer Speakers",
                             "Audio Cables","DAC Audio Devices","USB Audio Devices"]

    if request.method == "POST":
        color = request.POST.get("color", "").strip()
        ram = request.POST.get("ram", "").strip()
        storage = request.POST.get("storage", "").strip()
        connectivity = request.POST.get("connectivity", "").strip()
        battery_life = request.POST.get("battery_life", "").strip()
        sku = request.POST.get("sku", "").strip()
        price = request.POST.get("price", "0")
        discount_price = request.POST.get("discount_price", "0") or 0
        stock_quantity = request.POST.get("stock_quantity", "0") or 0
        main_image = request.FILES.get("main_image")
        base64_image = request.POST.get("main_image_base64")

        if base64_image:
            format, imgstr = base64_image.split(";base64,")
            ext = format.split("/")[-1]
            main_image = ContentFile(base64.b64decode(imgstr),name=f"main.{ext}")    
        gallery_images=request.FILES.getlist("variant_images")

        error = validate_variant(
            product=product,
            color=color,
            sku=sku,
            price=price,
            stock=stock_quantity,
            ram=ram,
            storage=storage,
            connectivity=connectivity,
            battery_life=battery_life,
            variant_id=variant.id if variant else None
        )

        if error:
            messages.error(request, error)
            return redirect(request.path)
        
        if variant is None and not main_image:
            messages.error(request, "Variant main image is required")
            return redirect(request.path)

        if variant is None and len(gallery_images) < 3:
            messages.error(request, "Upload minimum 3 variant gallery images")
            return redirect(request.path)

        if gallery_images and len(gallery_images) < 3:
            messages.error(request, "Upload minimum 3 variant gallery images")
            return redirect(request.path)

        if main_image:
            image_error = validate_image_file(main_image)
            if image_error:
                messages.error(request, image_error)
                return redirect(request.path)

        for image in gallery_images:
            image_error = validate_image_file(image)
            if image_error:
                messages.error(request, image_error)
                return redirect(request.path)

        if variant is None:
            variant = ProductVariant(product=product)

        variant.color = color
        variant.sku = sku
        variant.price = price
        variant.discount_price = discount_price
        variant.stock_quantity = stock_quantity
        variant.is_active = True if request.POST.get("is_active") else False
        variant.is_default = True if request.POST.get("is_default") else False

        if main_image:
            variant.main_image = main_image

        if product.category.type == "mobiles":
            variant.ram = ram
            variant.storage = storage
            variant.connectivity = None
            variant.battery_life = None
        else:
            variant.ram = None
            variant.storage = None
            variant.connectivity = connectivity
            variant.battery_life = battery_life

        variant.save()

        if variant.is_default:
            ProductVariant.objects.filter(product=product).exclude(id=variant.id).update(is_default=False)

        if gallery_images:
            variant.images.all().delete()

            for image in gallery_images:
                VariantImage.objects.create(
                    variant=variant,
                    image=image
                )
   

        messages.success(request, "Variant saved successfully")
        return redirect("variant_list", product_id=product.id)

    return render(request, "catalog/variant_form.html", {
        "product": product,
        "variant": variant,
        "title": title,
        "is_wired":product.category.category_name in wired_categories,
        "admin_name": admin_name(request),
    })
    
@login_required(login_url="admin_login")
@user_passes_test(is_admin, login_url="admin_login")
def delete_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product_id = variant.product.id
    variant.is_deleted = True
    variant.is_active=False
    variant.save()

    messages.success(request, "Variant deleted successfully")
    return redirect("variant_list", product_id=product_id)

