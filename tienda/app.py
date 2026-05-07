from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave-secreta-dev-2024')

# Base de datos: usa DATABASE_URL en producción, SQLite en local
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///tienda.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─────────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────────

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    es_admin = db.Column(db.Boolean, default=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=10)
    categoria = db.Column(db.String(80), nullable=False)
    imagen_url = db.Column(db.String(300), default='')
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)


class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    estado = db.Column(db.String(50), default='pendiente')
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.relationship('Usuario', backref='pedidos')
    items = db.relationship('ItemPedido', backref='pedido', lazy=True)


class ItemPedido(db.Model):
    __tablename__ = 'items_pedido'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    producto = db.relationship('Producto')


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def usuario_actual():
    if 'usuario_id' in session:
        return Usuario.query.get(session['usuario_id'])
    return None

def carrito_count():
    carrito = session.get('carrito', {})
    return sum(carrito.values())


# ─────────────────────────────────────────────
# RUTAS PRINCIPALES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    productos = Producto.query.filter(Producto.stock > 0).order_by(Producto.creado_en.desc()).limit(8).all()
    categorias = db.session.query(Producto.categoria).distinct().all()
    categorias = [c[0] for c in categorias]
    return render_template('index.html',
                           productos=productos,
                           categorias=categorias,
                           usuario=usuario_actual(),
                           carrito_count=carrito_count())


@app.route('/catalogo')
def catalogo():
    categoria = request.args.get('categoria', '')
    q = request.args.get('q', '')
    query = Producto.query
    if categoria:
        query = query.filter_by(categoria=categoria)
    if q:
        query = query.filter(Producto.nombre.ilike(f'%{q}%'))
    productos = query.order_by(Producto.nombre).all()
    categorias = db.session.query(Producto.categoria).distinct().all()
    categorias = [c[0] for c in categorias]
    return render_template('catalogo.html',
                           productos=productos,
                           categorias=categorias,
                           categoria_actual=categoria,
                           busqueda=q,
                           usuario=usuario_actual(),
                           carrito_count=carrito_count())


@app.route('/producto/<int:id>')
def producto_detalle(id):
    p = Producto.query.get_or_404(id)
    relacionados = Producto.query.filter(
        Producto.categoria == p.categoria,
        Producto.id != p.id,
        Producto.stock > 0
    ).limit(4).all()
    return render_template('producto.html',
                           producto=p,
                           relacionados=relacionados,
                           usuario=usuario_actual(),
                           carrito_count=carrito_count())


# ─────────────────────────────────────────────
# CARRITO
# ─────────────────────────────────────────────

@app.route('/carrito')
def ver_carrito():
    carrito = session.get('carrito', {})
    items = []
    total = 0
    for pid_str, cantidad in carrito.items():
        p = Producto.query.get(int(pid_str))
        if p:
            subtotal = p.precio * cantidad
            total += subtotal
            items.append({'producto': p, 'cantidad': cantidad, 'subtotal': subtotal})
    return render_template('carrito.html',
                           items=items,
                           total=total,
                           usuario=usuario_actual(),
                           carrito_count=carrito_count())


@app.route('/carrito/agregar/<int:pid>', methods=['POST'])
def agregar_carrito(pid):
    p = Producto.query.get_or_404(pid)
    carrito = session.get('carrito', {})
    key = str(pid)
    carrito[key] = carrito.get(key, 0) + 1
    session['carrito'] = carrito
    flash(f'"{p.nombre}" agregado al carrito.', 'success')
    return redirect(request.referrer or url_for('catalogo'))


@app.route('/carrito/quitar/<int:pid>', methods=['POST'])
def quitar_carrito(pid):
    carrito = session.get('carrito', {})
    key = str(pid)
    if key in carrito:
        if carrito[key] > 1:
            carrito[key] -= 1
        else:
            del carrito[key]
    session['carrito'] = carrito
    return redirect(url_for('ver_carrito'))


@app.route('/carrito/vaciar', methods=['POST'])
def vaciar_carrito():
    session['carrito'] = {}
    return redirect(url_for('ver_carrito'))


# ─────────────────────────────────────────────
# CHECKOUT / PEDIDO
# ─────────────────────────────────────────────

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not usuario_actual():
        flash('Debes iniciar sesión para realizar un pedido.', 'warning')
        return redirect(url_for('login'))
    carrito = session.get('carrito', {})
    if not carrito:
        return redirect(url_for('ver_carrito'))
    items = []
    total = 0
    for pid_str, cantidad in carrito.items():
        p = Producto.query.get(int(pid_str))
        if p:
            subtotal = p.precio * cantidad
            total += subtotal
            items.append({'producto': p, 'cantidad': cantidad, 'subtotal': subtotal})
    if request.method == 'POST':
        usuario = usuario_actual()
        pedido = Pedido(usuario_id=usuario.id, total=total, estado='confirmado')
        db.session.add(pedido)
        db.session.flush()
        for item in items:
            ip = ItemPedido(
                pedido_id=pedido.id,
                producto_id=item['producto'].id,
                cantidad=item['cantidad'],
                precio_unitario=item['producto'].precio
            )
            item['producto'].stock = max(0, item['producto'].stock - item['cantidad'])
            db.session.add(ip)
        db.session.commit()
        session['carrito'] = {}
        flash(f'¡Pedido #{pedido.id} confirmado con éxito!', 'success')
        return redirect(url_for('mis_pedidos'))
    return render_template('checkout.html',
                           items=items,
                           total=total,
                           usuario=usuario_actual(),
                           carrito_count=carrito_count())


@app.route('/mis-pedidos')
def mis_pedidos():
    if not usuario_actual():
        return redirect(url_for('login'))
    pedidos = Pedido.query.filter_by(usuario_id=session['usuario_id']).order_by(Pedido.creado_en.desc()).all()
    return render_template('mis_pedidos.html',
                           pedidos=pedidos,
                           usuario=usuario_actual(),
                           carrito_count=carrito_count())


# ─────────────────────────────────────────────
# AUTENTICACIÓN
# ─────────────────────────────────────────────

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        if Usuario.query.filter_by(email=email).first():
            flash('Ese correo ya está registrado.', 'danger')
            return redirect(url_for('registro'))
        u = Usuario(nombre=nombre, email=email)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        session['usuario_id'] = u.id
        flash(f'¡Bienvenido, {u.nombre}!', 'success')
        return redirect(url_for('index'))
    return render_template('registro.html', usuario=None, carrito_count=carrito_count())


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        u = Usuario.query.filter_by(email=email).first()
        if u and u.check_password(password):
            session['usuario_id'] = u.id
            flash(f'¡Hola de nuevo, {u.nombre}!', 'success')
            return redirect(url_for('index'))
        flash('Correo o contraseña incorrectos.', 'danger')
    return render_template('login.html', usuario=None, carrito_count=carrito_count())


@app.route('/logout')
def logout():
    session.pop('usuario_id', None)
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('index'))


# ─────────────────────────────────────────────
# PANEL ADMIN
# ─────────────────────────────────────────────

@app.route('/admin')
def admin():
    u = usuario_actual()
    if not u or not u.es_admin:
        flash('Acceso restringido.', 'danger')
        return redirect(url_for('index'))
    productos = Producto.query.order_by(Producto.creado_en.desc()).all()
    pedidos = Pedido.query.order_by(Pedido.creado_en.desc()).limit(10).all()
    total_ventas = db.session.query(db.func.sum(Pedido.total)).scalar() or 0
    return render_template('admin.html',
                           productos=productos,
                           pedidos=pedidos,
                           total_ventas=total_ventas,
                           usuario=u,
                           carrito_count=carrito_count())


@app.route('/admin/producto/nuevo', methods=['GET', 'POST'])
def admin_nuevo_producto():
    u = usuario_actual()
    if not u or not u.es_admin:
        return redirect(url_for('index'))
    if request.method == 'POST':
        p = Producto(
            nombre=request.form['nombre'],
            descripcion=request.form['descripcion'],
            precio=float(request.form['precio']),
            stock=int(request.form['stock']),
            categoria=request.form['categoria'],
            imagen_url=request.form.get('imagen_url', '')
        )
        db.session.add(p)
        db.session.commit()
        flash('Producto agregado.', 'success')
        return redirect(url_for('admin'))
    return render_template('admin_producto.html', producto=None, usuario=u, carrito_count=carrito_count())


@app.route('/admin/producto/editar/<int:id>', methods=['GET', 'POST'])
def admin_editar_producto(id):
    u = usuario_actual()
    if not u or not u.es_admin:
        return redirect(url_for('index'))
    p = Producto.query.get_or_404(id)
    if request.method == 'POST':
        p.nombre = request.form['nombre']
        p.descripcion = request.form['descripcion']
        p.precio = float(request.form['precio'])
        p.stock = int(request.form['stock'])
        p.categoria = request.form['categoria']
        p.imagen_url = request.form.get('imagen_url', '')
        db.session.commit()
        flash('Producto actualizado.', 'success')
        return redirect(url_for('admin'))
    return render_template('admin_producto.html', producto=p, usuario=u, carrito_count=carrito_count())


@app.route('/admin/producto/eliminar/<int:id>', methods=['POST'])
def admin_eliminar_producto(id):
    u = usuario_actual()
    if not u or not u.es_admin:
        return redirect(url_for('index'))
    p = Producto.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash('Producto eliminado.', 'success')
    return redirect(url_for('admin'))


# ─────────────────────────────────────────────
# API REST (para demostrar Sistemas Distribuidos)
# ─────────────────────────────────────────────

@app.route('/api/productos')
def api_productos():
    productos = Producto.query.filter(Producto.stock > 0).all()
    return jsonify([{
        'id': p.id,
        'nombre': p.nombre,
        'precio': p.precio,
        'stock': p.stock,
        'categoria': p.categoria
    } for p in productos])


@app.route('/api/productos/<int:id>')
def api_producto(id):
    p = Producto.query.get_or_404(id)
    return jsonify({
        'id': p.id,
        'nombre': p.nombre,
        'descripcion': p.descripcion,
        'precio': p.precio,
        'stock': p.stock,
        'categoria': p.categoria
    })


# ─────────────────────────────────────────────
# INICIALIZACIÓN
# ─────────────────────────────────────────────

def seed_data():
    if Producto.query.count() == 0:
        productos = [
            Producto(nombre='Laptop UltraBook Pro', descripcion='Laptop de alto rendimiento con procesador i7, 16GB RAM, SSD 512GB. Ideal para estudiantes y profesionales.', precio=2499.99, stock=15, categoria='Tecnología', imagen_url='https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400'),
            Producto(nombre='Auriculares Bluetooth X200', descripcion='Auriculares inalámbricos con cancelación de ruido activa, 30h de batería y sonido premium.', precio=149.99, stock=30, categoria='Tecnología', imagen_url='https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400'),
            Producto(nombre='Mochila Urbana Explorer', descripcion='Mochila resistente al agua con compartimento para laptop 15", múltiples bolsillos y diseño ergonómico.', precio=89.99, stock=25, categoria='Accesorios', imagen_url='https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400'),
            Producto(nombre='Teclado Mecánico RGB', descripcion='Teclado mecánico con switches Cherry MX, retroiluminación RGB personalizable y estructura de aluminio.', precio=199.99, stock=20, categoria='Tecnología', imagen_url='https://images.unsplash.com/photo-1541140532154-b024d705b90a?w=400'),
            Producto(nombre='Libro: Python para todos', descripcion='Guía completa de Python desde cero hasta nivel avanzado. Incluye proyectos prácticos y ejercicios.', precio=45.00, stock=50, categoria='Libros', imagen_url='https://images.unsplash.com/photo-1532012197267-da84d127e765?w=400'),
            Producto(nombre='Mouse Ergonómico Silent', descripcion='Mouse inalámbrico silencioso con diseño ergonómico, DPI ajustable y batería de larga duración.', precio=59.99, stock=40, categoria='Tecnología', imagen_url='https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400'),
            Producto(nombre='Botella Térmica 750ml', descripcion='Botella de acero inoxidable, mantiene bebidas frías 24h y calientes 12h. Libre de BPA.', precio=29.99, stock=60, categoria='Accesorios', imagen_url='https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=400'),
            Producto(nombre='Cuaderno de Diseño A4', descripcion='Cuaderno de 200 páginas con papel de alta calidad para bocetos, notas y diseño creativo.', precio=18.50, stock=80, categoria='Libros', imagen_url='https://images.unsplash.com/photo-1517842645767-c639042777db?w=400'),
        ]
        for p in productos:
            db.session.add(p)

        admin = Usuario(nombre='Admin', email='admin@tienda.com', es_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✅ Datos iniciales cargados.")


with app.app_context():
    db.create_all()
    seed_data()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
