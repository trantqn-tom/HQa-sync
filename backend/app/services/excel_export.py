from openpyxl import Workbook


workbook = Workbook(write_only=True)
worksheet = workbook.create_sheet("Listings")

worksheet.append(
    [
        "Marketplace",
        "Listing ID",
        "Title",
        "Price",
        "Status",
    ]
)

listings = [
    {
        "marketplace": "ebay",
        "listing_id": "123",
        "title": "JBL Speaker",
        "price": 499.99,
        "status": "ACTIVE",
    },
    {
        "marketplace": "ebay",
        "listing_id": "456",
        "title": "AR Speaker",
        "price": 799.99,
        "status": "ENDED",
    },
]

for listing in listings:
    worksheet.append(
        [
            listing["marketplace"],
            listing["listing_id"],
            listing["title"],
            listing["price"],
            listing["status"],
        ]
    )

workbook.save("listings.xlsx")
