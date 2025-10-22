# # inventory/routes.py
# from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
# from flask_login import login_required, current_user
# from datetime import datetime
# from models import db  # your central db instance
# # import inventory models (adjust import path if you put models in central models.py)
# from inventory.models import Item, SerialItem, GoodsIn, GoodsInLine, GoodsOut, GoodsOutLine, InventoryTransaction
#
# inventory_bp = Blueprint('inventory', __name__, template_folder='templates/inventory')
#
# # Dashboard - summary
# @inventory_bp.route('/')
# @login_required
# def inventory_dashboard():
#     # totals
#     total_items = Item.query.count()
#     total_serials = SerialItem.query.count()
#     in_count = SerialItem.query.filter_by(status='IN').count()
#     out_count = SerialItem.query.filter_by(status='OUT').count()
#     damaged_count = SerialItem.query.filter_by(status='DAMAGED').count()
#
#     # recent activity
#     recent_in = GoodsIn.query.order_by(GoodsIn.created_at.desc()).limit(5).all()
#     recent_out = GoodsOut.query.order_by(GoodsOut.created_at.desc()).limit(5).all()
#
#     return render_template('inventory/dashboard.html',
#                            total_items=total_items,
#                            total_serials=total_serials,
#                            in_count=in_count,
#                            out_count=out_count,
#                            damaged_count=damaged_count,
#                            recent_in=recent_in,
#                            recent_out=recent_out)
#
# # Stock table
# @inventory_bp.route('/stock')
# @login_required
# def stock_table():
#     # optional filters
#     status = request.args.get('status')
#     q = request.args.get('q','').strip()
#
#     query = SerialItem.query.join(Item)
#     if status:
#         query = query.filter(SerialItem.status==status)
#     if q:
#         qlike = f"%{q}%"
#         query = query.filter((SerialItem.serial_number.ilike(qlike)) | (Item.name.ilike(qlike)) | (SerialItem.billed_to.ilike(qlike)))
#
#     serials = query.order_by(SerialItem.created_at.desc()).limit(500).all()
#     statuses = ['IN','OUT','RESERVED','DAMAGED','LOST']
#     return render_template('inventory/stock_table.html', serials=serials, statuses=statuses, status=status, q=q)
#
# # Recent goods-in / goods-out listing (combined)
# @inventory_bp.route('/recent')
# @login_required
# def recent_transactions():
#     # combine last 50 transactions by created_at
#     ins = db.session.query(GoodsIn.id.label('id'), GoodsIn.ref_no.label('ref_no'),
#                            GoodsIn.vendor.label('party'), GoodsIn.arrived_date.label('date'),
#                            db.literal('IN').label('type'), GoodsIn.created_at.label('created_at')).all()
#     outs = db.session.query(GoodsOut.id.label('id'), GoodsOut.ref_no.label('ref_no'),
#                            GoodsOut.to_customer.label('party'), GoodsOut.sent_date.label('date'),
#                            db.literal('OUT').label('type'), GoodsOut.created_at.label('created_at')).all()
#     # SQLAlchemy mixing like above returns plain rows; simpler: fetch separately and merge in python
#     recent_in = GoodsIn.query.order_by(GoodsIn.created_at.desc()).limit(25).all()
#     recent_out = GoodsOut.query.order_by(GoodsOut.created_at.desc()).limit(25).all()
#     return render_template('inventory/recent_transactions.html', recent_in=recent_in, recent_out=recent_out)
#
# # AJAX serial lookup (API) - returns JSON
# @inventory_bp.route('/api/serial_lookup')
# @login_required
# def api_serial_lookup():
#     s = request.args.get('serial','').strip()
#     if not s:
#         return jsonify({'error': 'serial required'}), 400
#     # try exact first, else ilike
#     serials = SerialItem.query.filter(SerialItem.serial_number.ilike(f"%{s}%")).limit(10).all()
#     items = []
#     for si in serials:
#         items.append({
#             'serial_item_id': si.id,
#             'serial_number': si.serial_number,
#             'item_id': si.item_id,
#             'item_name': si.item.name if si.item else '',
#             'status': si.status,
#             'location': si.location,
#             'billed_to': si.billed_to
#         })
#     return jsonify(items)
#
# # Link to goods_in_add and goods_out_add assumed present (from earlier)
# @inventory_bp.route('/goods-in/add', methods=['GET','POST'])
# @login_required
# def goods_in_add():
#     # reuse existing implementation or redirect to main goods-in route
#     from inventory.routes_goods import goods_in_add as goods_in_impl  # optional separation
#     return goods_in_impl()
#
# @inventory_bp.route('/goods-out/add', methods=['GET','POST'])
# @login_required
# def goods_out_add():
#     from inventory.routes_goods import goods_out_add as goods_out_impl
#     return goods_out_impl()
#
# # Optional API for serial status change (mark damaged, return, etc.)
# @inventory_bp.route('/api/serial/<int:serial_id>/status', methods=['POST'])
# @login_required
# def api_change_serial_status(serial_id):
#     new_status = request.form.get('status')
#     note = request.form.get('note')
#     s = SerialItem.query.get_or_404(serial_id)
#     old = s.status
#     s.status = new_status
#     db.session.add(s)
#     tx = InventoryTransaction(serial_item_id=s.id, item_id=s.item_id, change_type='status_change', note=f"{old}->{new_status}. {note or ''}", created_by=current_user.id)
#     db.session.add(tx)
#     db.session.commit()
#     return jsonify({'success': True, 'serial_id': s.id, 'new_status': s.status})



# inventory/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import func
from models import db as _db  # fallback: your main models.py must expose db
db = _db

from sqlalchemy import func



# Try to import inventory models from inventory.models; fallback to central models
try:
    from inventory.models import Item, SerialItem, GoodsIn, GoodsInLine, GoodsOut, GoodsOutLine, InventoryTransaction
except Exception:
    # If you kept inventory models inside central models.py, try to import them from there
    try:
        from models import Item, SerialItem, GoodsIn, GoodsInLine, GoodsOut, GoodsOutLine, InventoryTransaction
    except Exception as e:
        raise ImportError("Could not import inventory models. Ensure inventory.models or models contains the needed classes.") from e

inventory_bp = Blueprint('inventory', __name__, template_folder='templates/inventory')


@inventory_bp.route('/api/add_item', methods=['POST'])
@login_required
def api_add_item():
    # expects form data: name, item_type (optional), csrf_token
    name = request.form.get('name', '').strip()
    item_type = request.form.get('item_type', '').strip()

    if not name:
        return jsonify({'success': False, 'error': 'Name required'}), 400
    if len(name) > 100:
        return jsonify({'success': False, 'error': 'Name too long (max 100)'}), 400

    # case-insensitive check existing
    existing = Item.query.filter(func.lower(Item.name) == name.lower()).first()
    if existing:
        return jsonify({'success': True, 'item_id': existing.id, 'name': existing.name, 'exists': True})

    # create
    new_item = Item(name=name, item_type=item_type or None)
    db.session.add(new_item)
    db.session.commit()
    return jsonify({'success': True, 'item_id': new_item.id, 'name': new_item.name})




# -------------------------
# Dashboard & listings
# -------------------------
@inventory_bp.route('/')
@login_required
def inventory_dashboard():
    total_items = Item.query.count()
    total_serials = SerialItem.query.count()
    in_count = SerialItem.query.filter_by(status='IN').count()
    out_count = SerialItem.query.filter_by(status='OUT').count()
    damaged_count = SerialItem.query.filter_by(status='DAMAGED').count()

    recent_in = GoodsIn.query.order_by(GoodsIn.created_at.desc()).limit(6).all()
    recent_out = GoodsOut.query.order_by(GoodsOut.created_at.desc()).limit(6).all()

    return render_template('inventory/dashboard.html',
                           total_items=total_items,
                           total_serials=total_serials,
                           in_count=in_count,
                           out_count=out_count,
                           damaged_count=damaged_count,
                           recent_in=recent_in,
                           recent_out=recent_out)

@inventory_bp.route('/stock')
@login_required
def stock_table():
    status = request.args.get('status')
    q = request.args.get('q','').strip()

    query = SerialItem.query.join(Item)
    if status:
        query = query.filter(SerialItem.status==status)
    if q:
        qlike = f"%{q}%"
        query = query.filter((SerialItem.serial_number.ilike(qlike)) | (Item.name.ilike(qlike)) | (SerialItem.billed_to.ilike(qlike)))

    serials = query.order_by(SerialItem.created_at.desc()).limit(500).all()
    statuses = ['IN','OUT','RESERVED','DAMAGED','LOST']
    return render_template('inventory/stock_table.html', serials=serials, statuses=statuses, status=status, q=q)

@inventory_bp.route('/recent')
@login_required
def recent_transactions():
    recent_in = GoodsIn.query.order_by(GoodsIn.created_at.desc()).limit(25).all()
    recent_out = GoodsOut.query.order_by(GoodsOut.created_at.desc()).limit(25).all()
    return render_template('inventory/recent_transactions.html', recent_in=recent_in, recent_out=recent_out)

# -------------------------
# API endpoints
# -------------------------
@inventory_bp.route('/api/serial_lookup')
@login_required
def api_serial_lookup():
    s = request.args.get('serial','').strip()
    if not s:
        return jsonify({'error': 'serial required'}), 400
    serials = SerialItem.query.filter(SerialItem.serial_number.ilike(f"%{s}%")).limit(10).all()
    items = []
    for si in serials:
        items.append({
            'serial_item_id': si.id,
            'serial_number': si.serial_number,
            'item_id': si.item_id,
            'item_name': si.item.name if si.item is not None else '',
            'status': si.status,
            'location': si.location,
            'billed_to': si.billed_to
        })
    return jsonify(items)

@inventory_bp.route('/api/serial/<int:serial_id>/status', methods=['POST'])
@login_required
def api_change_serial_status(serial_id):
    new_status = request.form.get('status')
    note = request.form.get('note')
    if not new_status:
        return jsonify({'error': 'status required'}), 400
    s = SerialItem.query.get_or_404(serial_id)
    old = s.status
    s.status = new_status
    db.session.add(s)
    tx = InventoryTransaction(serial_item_id=s.id, item_id=s.item_id, change_type='status_change',
                               note=f"{old}->{new_status}. {note or ''}", created_by=current_user.id)
    db.session.add(tx)
    db.session.commit()
    return jsonify({'success': True, 'serial_id': s.id, 'new_status': s.status})

# -------------------------
# Goods IN
# -------------------------
@inventory_bp.route('/goods-in/add', methods=['GET', 'POST'])
@login_required
def goods_in_add():
    if request.method == 'POST':
        ref_no = request.form.get('ref_no')
        vendor = request.form.get('vendor')
        arrived_date_raw = request.form.get('arrived_date', '').strip()
        arrived_date = None
        if arrived_date_raw:
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    arrived_date = datetime.strptime(arrived_date_raw, fmt)
                    break
                except ValueError:
                    continue

        item_ids = request.form.getlist('item_id[]')
        serials = request.form.getlist('serial_number[]')
        billed_tos = request.form.getlist('billed_to[]')

        if not (item_ids and serials) or len(item_ids) != len(serials):
            flash('Invalid input rows', 'error')
            return redirect(url_for('inventory.goods_in_add'))

        goodsin = GoodsIn(ref_no=ref_no or None, vendor=vendor or None, arrived_date=arrived_date, created_by=current_user.id)
        db.session.add(goodsin)
        db.session.flush()  # get goodsin.id

        for i, sn in enumerate(serials):
            try:
                item_id = int(item_ids[i])
            except Exception:
                db.session.rollback()
                flash('Invalid item selection', 'error')
                return redirect(url_for('inventory.goods_in_add'))

            serial_number = sn.strip()
            billed_to = billed_tos[i] if i < len(billed_tos) else None

            existing = SerialItem.query.filter_by(item_id=item_id, serial_number=serial_number).first()
            if existing:
                # update some fields and mark IN
                existing.status = 'IN'
                existing.purchase_from = vendor or existing.purchase_from
                existing.arrived_date = arrived_date or existing.arrived_date
                existing.billed_to = billed_to or existing.billed_to
                db.session.add(existing)
                serial_item = existing
            else:
                serial_item = SerialItem(item_id=item_id, serial_number=serial_number,
                                         purchase_from=vendor or None, arrived_date=arrived_date,
                                         billed_to=billed_to or None, status='IN', created_by=current_user.id)
                db.session.add(serial_item)
                db.session.flush()

            line = GoodsInLine(goodsin_id=goodsin.id, item_id=item_id, serial_number=serial_number,
                               billed_to=billed_to or None, serial_item_id=serial_item.id)
            db.session.add(line)

            tx = InventoryTransaction(serial_item_id=serial_item.id, item_id=item_id, change_type='goods_in',
                                      ref_id=goodsin.id, created_by=current_user.id)
            db.session.add(tx)

        db.session.commit()
        flash('Goods recorded (IN) and serials added/updated.', 'success')
        return redirect(url_for('inventory.inventory_dashboard'))

    items = Item.query.order_by(Item.name).all()
    return render_template('inventory/goods_in_form.html', items=items)

# -------------------------
# Goods OUT
# -------------------------
@inventory_bp.route('/goods-out/add', methods=['GET', 'POST'])
@login_required
def goods_out_add():
    if request.method == 'POST':
        ref_no = request.form.get('ref_no')
        to_customer = request.form.get('to_customer')
        sent_via = request.form.get('sent_via')
        parcel_details = request.form.get('parcel_details')
        sent_date_raw = request.form.get('sent_date', '').strip()
        sent_date = None
        if sent_date_raw:
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    sent_date = datetime.strptime(sent_date_raw, fmt)
                    break
                except ValueError:
                    continue

        item_ids = request.form.getlist('item_id[]')
        serials = request.form.getlist('serial_number[]')

        if not (item_ids and serials) or len(item_ids) != len(serials):
            flash('Invalid input rows', 'error')
            return redirect(url_for('inventory.goods_out_add'))

        goodsout = GoodsOut(ref_no=ref_no or None, to_customer=to_customer or None,
                            sent_via=sent_via or None, parcel_details=parcel_details or None,
                            sent_date=sent_date, created_by=current_user.id)
        db.session.add(goodsout)
        db.session.flush()

        for i, sn in enumerate(serials):
            try:
                item_id = int(item_ids[i])
            except Exception:
                db.session.rollback()
                flash('Invalid item selection', 'error')
                return redirect(url_for('inventory.goods_out_add'))

            serial_number = sn.strip()
            serial_item = SerialItem.query.filter_by(item_id=item_id, serial_number=serial_number).first()
            if not serial_item:
                db.session.rollback()
                flash(f"Serial {serial_number} for item {item_id} not found or not in stock.", 'error')
                return redirect(url_for('inventory.inventory_dashboard'))

            if serial_item.status != 'IN':
                db.session.rollback()
                flash(f"Serial {serial_number} status is {serial_item.status} — cannot dispatch.", 'error')
                return redirect(url_for('inventory.inventory_dashboard'))

            serial_item.status = 'OUT'
            db.session.add(serial_item)
            db.session.flush()

            line = GoodsOutLine(goodsout_id=goodsout.id, item_id=item_id, serial_number=serial_number, serial_item_id=serial_item.id)
            db.session.add(line)

            tx = InventoryTransaction(serial_item_id=serial_item.id, item_id=item_id, change_type='goods_out',
                                      ref_id=goodsout.id, created_by=current_user.id)
            db.session.add(tx)

        db.session.commit()
        flash('Goods dispatched (OUT) and serial statuses updated.', 'success')
        return redirect(url_for('inventory.inventory_dashboard'))

    items = Item.query.order_by(Item.name).all()
    return render_template('inventory/goods_out_form.html', items=items)
