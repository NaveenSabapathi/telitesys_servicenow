# inventory/models.py
from datetime import datetime
from models import db, User  # adjust import to match your project

class Item(db.Model):
    __tablename__ = 'inv_item'
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), unique=True, nullable=True)
    name = db.Column(db.String(200), nullable=False)
    item_type = db.Column(db.String(100))   # e.g., Accessory, Laptop, Charger
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationship to serials
    serials = db.relationship('SerialItem', backref='item', lazy=True)

    def current_stock(self):
        # Count serials currently IN
        return SerialItem.query.filter_by(item_id=self.id, status='IN').count()

class SerialItem(db.Model):
    """
    Track each physical unit by serial number.
    Status: IN, OUT, RESERVED, DAMAGED, LOST
    """
    __tablename__ = 'inv_serial'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inv_item.id'), nullable=False)
    serial_number = db.Column(db.String(200), nullable=False, index=True)
    purchase_from = db.Column(db.String(200))
    arrived_date = db.Column(db.DateTime)
    billed_to = db.Column(db.String(200))     # if sold / billed to someone on arrival
    location = db.Column(db.String(200))      # optional shelf / godown bin
    status = db.Column(db.String(30), default='IN')  # IN / OUT / RESERVED / DAMAGED
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('item_id', 'serial_number', name='uq_item_serial'),
    )

    # convenience
    def is_in(self): return self.status == 'IN'

class GoodsIn(db.Model):
    __tablename__ = 'inv_goods_in'
    id = db.Column(db.Integer, primary_key=True)
    ref_no = db.Column(db.String(120), nullable=True)    # invoice or GRN number
    vendor = db.Column(db.String(200))                   # purchase_from replicate
    arrived_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    lines = db.relationship('GoodsInLine', backref='goodsin', lazy=True, cascade="all, delete-orphan")

class GoodsInLine(db.Model):
    __tablename__ = 'inv_goods_in_line'
    id = db.Column(db.Integer, primary_key=True)
    goodsin_id = db.Column(db.Integer, db.ForeignKey('inv_goods_in.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inv_item.id'), nullable=False)
    serial_number = db.Column(db.String(200), nullable=False)
    billed_to = db.Column(db.String(200))
    # save a denormalized pointer to SerialItem if exists:
    serial_item_id = db.Column(db.Integer, db.ForeignKey('inv_serial.id'), nullable=True)

class GoodsOut(db.Model):
    __tablename__ = 'inv_goods_out'
    id = db.Column(db.Integer, primary_key=True)
    ref_no = db.Column(db.String(120), nullable=True)   # outward document / challan / invoice
    to_customer = db.Column(db.String(200))
    sent_via = db.Column(db.String(100))   # bus, parcel, courier
    parcel_details = db.Column(db.Text)    # AWB, tracking no, bus no etc.
    sent_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    lines = db.relationship('GoodsOutLine', backref='goodsout', lazy=True, cascade="all, delete-orphan")

class GoodsOutLine(db.Model):
    __tablename__ = 'inv_goods_out_line'
    id = db.Column(db.Integer, primary_key=True)
    goodsout_id = db.Column(db.Integer, db.ForeignKey('inv_goods_out.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inv_item.id'), nullable=False)
    serial_number = db.Column(db.String(200), nullable=False)
    serial_item_id = db.Column(db.Integer, db.ForeignKey('inv_serial.id'), nullable=True)

class InventoryTransaction(db.Model):
    __tablename__ = 'inv_transaction'
    id = db.Column(db.Integer, primary_key=True)
    serial_item_id = db.Column(db.Integer, db.ForeignKey('inv_serial.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('inv_item.id'))
    change_type = db.Column(db.String(50))   # goods_in, goods_out, status_change, adjustment
    ref_id = db.Column(db.Integer)           # id of GoodsIn or GoodsOut
    note = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
