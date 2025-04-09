import uuid


def gen(namespace, *args):
    name = bytes()
    for arg in args:
        if isinstance(arg, str):
            name += arg.encode("utf-8")
            name += b"\x00"

        elif isinstance(arg, bytes):
            name += arg
            name += b"\x00"

        else:
            assert False, f"Cannot encode {type(arg)}"

    return uuid.uuid5(uuid.UUID(namespace), name)


brand_uuid = gen("5269dfb7-1559-440a-85be-aba5f3eff2d2", "Prusament")
print(brand_uuid)

print(gen("616fc86d-7d99-4953-96c7-46d2836b9be9", brand_uuid.bytes, b"\x01"))
