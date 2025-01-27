from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import os
import pymysql
pymysql.install_as_MySQLdb()
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.secret_key = 'kayaabadi'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://ulowousrw0ogyvoj:4LBHdOCx4lQvcea7mBsA@b4a2bvewihwdrwvkpgpj-mysql.services.clever-cloud.com:3306/b4a2bvewihwdrwvkpgpj'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

print(generate_password_hash('admin', method='pbkdf2:sha256'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(100), nullable=True)  # Tambahkan atribut image
    products = db.relationship('Products', backref='category', lazy=True)




class Products(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    image = db.Column(db.String(100), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False, default="Anonymous")
    customer_phone = db.Column(db.String(15), nullable=False)
    customer_address = db.Column(db.String(255), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    shipping_method = db.Column(db.String(50), nullable=False)
    payment_status = db.Column(db.String(50), default='Pending')
    cart_data = db.Column(db.PickleType, nullable=False)
    is_locked = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()
    if not Admin.query.first():
        hashed_password = generate_password_hash('admin', method='pbkdf2:sha256')
        admin = Admin(username='admin', password=hashed_password)
        db.session.add(admin)
        db.session.commit()
        db.session.close()

with app.app_context():
    # Tambahkan kategori contoh
    if not Category.query.first():
        categories = ['Bahan Bangunan', 'Cat & Perlengkapan', 'Mur, Baut & Paku', 'Pintu dan Jendela', 'Pipa']
        for name in categories:
            category = Category(name=name)
            db.session.add(category)
        db.session.commit()

@app.route('/')
def home():
    products = Products.query.all()
    categories = Category.query.all()  # Ambil semua kategori
    return render_template('home.html', products=products, categories=categories)

@app.route('/products')
def products():
    products = Products.query.all()
    return render_template('products.html', products=products)

@app.route('/about')
def about():
    return render_template('tentangkami.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/category/<int:category_id>')
def products_by_category(category_id):
    category = Category.query.get_or_404(category_id)
    products = Products.query.filter_by(category_id=category_id).all()
    return render_template('products_by_category.html', category=category, products=products)

@app.route('/search', methods=['GET', 'POST'])
def search():
    query = request.args.get('search', '').strip()  # Ambil query dari URL
    if query:
        products = Products.query.filter(Products.name.ilike(f'%{query}%')).all()
    else:
        products = []
    return render_template('searchresults.html', products=products, query=query)


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Products.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

@app.route('/category/<int:category_id>')
def category_products(category_id):
    category = Category.query.get_or_404(category_id)
    products = Products.query.filter_by(category_id=category.id).all()
    return render_template('category_products.html', category=category, products=products)


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Products.query.get_or_404(product_id)
    cart = session.get('cart', [])

    existing_item = next((item for item in cart if item['id'] == product_id), None)
    if existing_item:
        existing_item['quantity'] += 1
    else:
        cart.append({
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'image': product.image,
            'quantity': 1
        })

    session['cart'] = cart
    session.modified = True

    return redirect(request.referrer or url_for('product_detail', product_id=product_id))

@app.route('/admin/category/add', methods=['GET', 'POST'])
def add_category():
    if 'admin' not in session:
        flash('Harap login sebagai admin.', 'danger')
        return redirect(url_for('loginadmin'))

    if request.method == 'POST':
        name = request.form['name']
        image = request.files.get('image')

        if not name:
            flash('Nama kategori wajib diisi.', 'danger')
            return redirect(request.url)

        filename = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_category = Category(name=name, image=filename)
        db.session.add(new_category)
        db.session.commit()

        flash('Kategori berhasil ditambahkan.', 'success')
        return redirect(url_for('homeadmin'))

    return render_template('add_category.html')

@app.route('/admin/category/edit/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    if 'admin' not in session:
        flash('Harap login sebagai admin.', 'danger')
        return redirect(url_for('loginadmin'))

    category = Category.query.get_or_404(category_id)

    if request.method == 'POST':
        category.name = request.form['name']
        image = request.files.get('image')

        if image and allowed_file(image.filename):
            if category.image:
                # Hapus gambar lama
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], category.image)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)

            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            category.image = filename

        db.session.commit()
        flash('Kategori berhasil diperbarui.', 'success')
        return redirect(url_for('homeadmin'))

    return render_template('edit_category.html', category=category)


@app.route('/cart', methods=['GET', 'POST'])
def view_cart():
    cart = session.get('cart', [])

    for item in cart:
        if 'quantity' not in item:
            item['quantity'] = 1

    if request.method == 'POST':
        product_id = int(request.form.get('product_id'))
        action = request.form.get('action')

        for item in cart:
            if item['id'] == product_id:
                if action == 'increase':
                    item['quantity'] += 1
                elif action == 'decrease':
                    if item['quantity'] > 1:
                        item['quantity'] -= 1
                    elif item['quantity'] == 1:
                        cart.remove(item)
                break

        session['cart'] = cart
        session.modified = True
        return redirect(url_for('view_cart'))

    cart_total = sum(item['price'] * item['quantity'] for item in cart)
    return render_template('cart.html', cart=cart, cart_total=cart_total)

@app.route('/pengahapusproduk/<int:product_id>', methods=['POST'])
def pengahapusproduk(product_id):
    cart = session.get('cart', [])
    cart = [item for item in cart if item['id'] != product_id]
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('view_cart'))

@app.route('/pembayaran', methods=['GET', 'POST'])
def pembayaran():
    cart = session.get('cart', [])
    if not cart:
        flash("Keranjang Anda kosong. Silakan tambah produk terlebih dahulu.", "warning")
        return redirect(url_for('home'))

    cart_total = sum(item['price'] * item['quantity'] for item in cart)

    if request.method == 'POST':
        name = request.form.get('first_name') + " " + request.form.get('last_name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        postal_code = request.form.get('postal_code')
        shipping_method = request.form.get('shipping_method')
        payment_method = request.form.get('payment_method')

        if not name or not phone or not address or not postal_code or not payment_method:
            flash("Mohon isi semua data dengan lengkap!", "danger")
            return redirect(request.url)

        new_order = Order(
            customer_name=name,
            customer_phone=phone,
            customer_address=address,
            total_price=cart_total,
            payment_method=payment_method,
            shipping_method=shipping_method,
            payment_status='Pending',
            cart_data=cart
        )
        db.session.add(new_order)
        db.session.commit()
        session.pop('cart', None)
        flash("Pesanan berhasil dibuat.", "success")
    
        if payment_method:
            flash(f"Pesanan Anda telah diterima. Silakan lanjutkan dengan {payment_method}.", "success")
            return redirect(url_for('payment_instructions', method=payment_method, total=cart_total))    
        else:
            flash("Silakan lengkapi detail tambahan untuk pembayaran.", "info")
            return redirect(url_for('payment_form'))

    return render_template('pembayaran.html', cart=cart, cart_total=cart_total)

@app.route('/instruksi/<payment_method>')
def payment_method(payment_method):
    if payment_method:
        flash(f"Pesanan Anda telah diterima. Silakan lanjutkan dengan {payment_method}.", "success")
        return redirect(url_for('payment_instructions', method=payment_method))
    else:
        flash("Silakan lengkapi detail tambahan untuk pembayaran.", "info")
        return redirect(url_for('payment_method'))
    

@app.route('/payment-instructions/<method>', methods=['GET', 'POST'])
def payment_instructions(method):
    cart_total = request.args.get('total', 0)  # Ambil total dari parameter URL
    return render_template(f'instructions/{method}.html', cart_total=cart_total)



@app.route('/admin/orders')
def pesananadmin():
    if 'admin' not in session:
        return redirect(url_for('loginadmin'))
    orders = Order.query.all()
    return render_template('pesananadmin.html', orders=orders)

@app.route('/admin/order/<int:order_id>/verify', methods=['POST'])
def verify_order(order_id):
    if 'admin' not in session:
        return redirect(url_for('loginadmin'))
    order = Order.query.get_or_404(order_id)
    if order.is_locked:
        flash("Pesanan sudah terkunci dan tidak dapat diubah.", "warning")
        return redirect(url_for('pesananadmin'))

    order.payment_status = 'Terverifikasi'
    # order.is_locked = True
    db.session.commit()
    flash('Pembayaran telah diverifikasi!', 'success')
    return redirect(url_for('pesananadmin'))


@app.route('/admin/order/<int:order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    if 'admin' not in session:
        return redirect(url_for('loginadmin'))
    
    order = Order.query.get_or_404(order_id)

    order.is_locked = False
    db.session.delete(order)
    db.session.commit()
    flash('Pesanan berhasil dihapus!', 'danger')
    return redirect(url_for('pesananadmin'))


@app.route('/pc', methods=['GET', 'POST'])
def pc():
    session.pop('cart', None)
    session.pop('checkout_complete', None)
    session.pop('payment_method', None)
    return render_template('pc.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def loginadmin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Admin.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password, password):
            session['admin'] = admin.username
            return redirect(url_for('homeadmin'))
        else:
            return render_template('loginadmin.html', error="Invalid credentials!")
    return render_template('loginadmin.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('loginadmin'))

@app.route('/admin')
def homeadmin():
    if 'admin' not in session:
        return redirect(url_for('loginadmin'))
    products = Products.query.all()
    return render_template('homeadmin.html', products=products)

@app.route('/admin/pengaturanproduk', methods=['GET', 'POST'])
def pengaturanproduk():
    if 'admin' not in session:
        return redirect(url_for('loginadmin'))

    if request.method == 'POST':
        print("Request files:", request.files)  # Debugging request.files
        print("Request form:", request.form)    # Debugging request.form

        try:
            name = request.form['name']
            price = float(request.form['price'])
            description = request.form['description']
            category_id = int(request.form['category'])

            file = request.files.get('image')  # Gunakan .get() untuk menghindari error
            if not file:
                flash("File gambar tidak ditemukan!", "danger")
                return redirect(request.url)

            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            else:
                flash("Format file tidak diizinkan!", "danger")
                return redirect(request.url)

            new_product = Products(name=name, price=price, description=description, image=filename, category_id=category_id)
            db.session.add(new_product)
            db.session.commit()
            flash("Produk berhasil ditambahkan!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Terjadi kesalahan: {e}", "danger")

        return redirect(url_for('homeadmin'))

    products = Products.query.all()
    categories = Category.query.all()
    return render_template('tambahproduk.html', products=products, categories=categories)



@app.route('/admin/tambahproduk', methods=['GET', 'POST'])  # Mengubah URL route
def tambahproduk():  # Mengubah nama fungsi
    if 'admin' not in session:
        return redirect(url_for('loginadmin'))

    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        category_id = int(request.form['category'])
        image = request.files['image']

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)

            new_product = Products(name=name, price=price, description=description, image=filename, category_id=category_id)
            db.session.add(new_product)
            db.session.commit()

        return redirect(url_for('homeadmin'))

    categories = Category.query.all()
    return render_template('tambahproduk.html', categories=categories)



@app.route('/admin/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'admin' not in session:
        flash('Harap login sebagai admin.', 'danger')
        return redirect(url_for('loginadmin'))

    product = Products.query.get_or_404(product_id)

    if request.method == 'POST':
        try:
            product.name = request.form['name']
            product.price = float(request.form['price'])
            product.description = request.form['description']

            image = request.files.get('image')
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(filepath)
                product.image = filename 

            db.session.commit()
            flash('Produk berhasil diperbarui!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat memperbarui produk: {e}', 'danger')

        return redirect(url_for('homeadmin'))

    return render_template('edit_product.html', product=product)

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/order/<int:order_id>')
def order_detail(order_id):
    # Ambil data order berdasarkan ID
    order = Order.query.get_or_404(order_id)
    
    # Mengirimkan data pesanan ke template
    return render_template('order_detail.html', order=order)

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    # Logic to delete the order by ID
    order = Order.query.get(order_id)
    if order:
        db.session.delete(order)
        db.session.commit()
    return redirect(url_for('pesananadmin'))




@app.route('/admin/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'admin' not in session:
        return redirect(url_for('loginadmin'))

    product = Products.query.get_or_404(product_id)

    if product.image:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image)
        if os.path.exists(image_path):
            os.remove(image_path)

    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('homeadmin'))


@app.route('/categories')
def categories():
    return redirect(url_for('categories'))

if __name__ == '__main__':
    app.run()


