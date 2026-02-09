
def serialize_device(device):
    return {
        "device_type": device.device_type,
        "device_name": device.device_name,
        "model": device.model,
        "serial_number": device.serial_number,
        "issue_description": device.issue_description,
        "assign_status": device.assign_status.value,
        "remark": device.remark,
        "received_date": device.received_date.isoformat(),
        "expected_delivery_date": device.expected_delivery_date.isoformat(),
        "delivery_date": device.delivery_date.isoformat() if device.delivery_date else None,
        "image_filename": device.image_filename
    }


def serialize_customer(customer):
    return {
        "name": customer.name,
        "location": customer.location,
        "whatsapp_number": customer.whatsapp_number
    }


def serialize_user(user):
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "phone_number": user.phone_number,
        "user_level": user.user_level
    }


def serialize_spare_parts(services):
    parts = []
    for service in services:
        for sp in service.spare_parts:
            parts.append({
                "spare_name": sp.spare_name,
                "cost": sp.cost
            })
    return parts