from barcode import Code128
from barcode.writer import ImageWriter

def create_barcode(text):
    barcode = Code128(text, writer=ImageWriter())
    filename = barcode.save(f"barcodes/{text}")
    print("Saved:", filename)

# Example:
create_barcode("PROD12345")
