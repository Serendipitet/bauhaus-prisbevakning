import unittest
from decimal import Decimal
from price_monitor import hamta_pris_fran_html, till_pris


class PrisParserTester(unittest.TestCase):
    def test_svenska_priser(self):
        self.assertEqual(till_pris("799,00 kr"), Decimal("799.00"))
        self.assertEqual(till_pris("1 299,00 kr"), Decimal("1299.00"))
        self.assertEqual(till_pris("1.299,00 kr"), Decimal("1299.00"))

    def test_jsonld_och_kampanjtext(self):
        html = '''<html><body><p>Köp för 1 000 kr och spara 20 %</p>
        <script type="application/ld+json">{"@context":"https://schema.org",
        "@type":"Product","name":"Fibrotech SPC Vit marmor",
        "offers":{"@type":"Offer","price":"799.00","priceCurrency":"SEK"}}
        </script></body></html>'''
        self.assertEqual(hamta_pris_fran_html(html), Decimal("799.00"))

    def test_magento_pris(self):
        html = '''<html><body><p>Köp för 1 000 kr</p>
        <div class="product-info-main"><span data-price-type="finalPrice">
        <span data-price-amount="699.00">699,00 kr</span>
        </span></div></body></html>'''
        self.assertEqual(hamta_pris_fran_html(html), Decimal("699.00"))

    def test_saknat_pris_misslyckas_hellre_an_gissar(self):
        with self.assertRaises(ValueError):
            hamta_pris_fran_html("<html><p>Köp för 1 000 kr, spara 20 %</p></html>")


if __name__ == "__main__":
    unittest.main()
