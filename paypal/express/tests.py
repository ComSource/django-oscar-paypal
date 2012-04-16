from decimal import Decimal as D
from unittest import TestCase
from mock import patch, Mock
from purl import URL
from django.contrib.sites.models import Site

from paypal import express
from paypal.express.models import Transaction
from paypal.express.facade import get_paypal_url, fetch_transaction_details


class ExpressTests(TestCase):

    def _test_set_call_returns_url(self):
        url = express.set(D('10.00'), 'GBP', 'http://localhost:8000/success',
                            'http://localhost:8000/error')
        print url


class TransactionTests(TestCase):

    def test_password_is_not_saved(self):
        payload = 'PAYMENTACTION=Sale&PAYERID=7ZTRBDFYYA47W&CURRENCYCODE=GBP&TOKEN=EC-9LW34435GU332960W&AMT=6.99&PWD=1432777837&VERSION=60.0&USER=test_1332777813_biz_api1.gmail.com&SIGNATURE=A22DCxaCv-WeMRC6ke.fAabwPrYNAH6IkVF8xxY9XZI3Qtl0q-2XLULA&METHOD=DoExpressCheckoutPayment'
        txn = Transaction.objects.create(raw_request=payload,
                                        response_time=0)
        self.assertTrue('1432777837' not in txn.raw_request)


class FacadeTests(TestCase):

    def test_domain_in_return_url_defaults_to_current_site(self):
        response_body = 'TOKEN=EC%2d6469953681606921P&TIMESTAMP=2012%2d03%2d26T17%3a19%3a38Z&CORRELATIONID=50a8d895e928f&ACK=Success&VERSION=60%2e0&BUILD=2649250'
        response = Mock()
        response.content = response_body
        response.status_code = 200
        with patch('requests.post') as post:
            post.return_value = response
            basket = Mock()
            basket.total_incl_tax = D('200')
            url_str = get_paypal_url(basket)
            return_url = URL.from_string(url_str).query_param('RETURNURL')
            site = Site.objects.get_current()
            self.assertTrue(site.domain in return_url)

    def tearDown(self):
        Transaction.objects.all().delete()


class MockedResponseTests(TestCase):

    def test_error_response_raises_exception(self):
        response_body = 'TIMESTAMP=2012%2d03%2d26T16%3a33%3a09Z&CORRELATIONID=3bea2076bb9c3&ACK=Failure&VERSION=0%2e000000&BUILD=2649250&L_ERRORCODE0=10002&L_SHORTMESSAGE0=Security%20error&L_LONGMESSAGE0=Security%20header%20is%20not%20valid&L_SEVERITYCODE0=Error'
        response = Mock()
        response.content = response_body
        response.status_code = 200
        with patch('requests.post') as post:
            post.return_value = response
            with self.assertRaises(express.PayPalError):
                url = express.set(D('10.00'), 'GBP', 'http://localhost:8000/success',
                                  'http://localhost:8000/error')


class SuccessResponseTests(TestCase):

    def setUp(self):
        response_body = 'TOKEN=EC%2d6469953681606921P&TIMESTAMP=2012%2d03%2d26T17%3a19%3a38Z&CORRELATIONID=50a8d895e928f&ACK=Success&VERSION=60%2e0&BUILD=2649250'
        response = Mock()
        response.content = response_body
        response.status_code = 200
        with patch('requests.post') as post:
            post.return_value = response
            self.url = express.set(D('10.00'), 'GBP', 'http://localhost:8000/success',
                                   'http://localhost:8000/error')

    def tearDown(self):
        Transaction.objects.all().delete()

    def test_success_response_returns_url(self):
        self.assertTrue(self.url.startswith('https://www.sandbox.paypal.com'))

    def test_success_response_creates_model(self):
        txn = Transaction.objects.get(correlation_id='50a8d895e928f')
        self.assertEqual(D('10.00'), txn.amount)
        self.assertEqual('GBP', txn.currency)
        self.assertEqual('Success', txn.ack)
        self.assertEqual('60.0', txn.version)
        self.assertEqual('EC-6469953681606921P', txn.token)
            

class MockedResponseTests(TestCase):
    token = ''
    response_body = ''

    def setUp(self):
        response = Mock()
        response.content = self.response_body
        response.status_code = 200
        with patch('requests.post') as post:
            post.return_value = response
            self.txn = fetch_transaction_details(self.token)

    def tearDown(self):
        Transaction.objects.all().delete()


class SuccessfulGetExpressCheckoutTests(MockedResponseTests):
    token = 'EC-9LW34435GU332960W'
    response_body = 'TOKEN=EC%2d9LW34435GU332960W&CHECKOUTSTATUS=PaymentActionNotInitiated&TIMESTAMP=2012%2d04%2d13T15%3a19%3a25Z&CORRELATIONID=83bda082c24d4&ACK=Success&VERSION=60%2e0&BUILD=2808426&EMAIL=david%2e_1332854868_per%40gmail%2ecom&PAYERID=7ZTRBDFYYA47W&PAYERSTATUS=verified&FIRSTNAME=David&LASTNAME=Winterbottom&COUNTRYCODE=GB&SHIPTONAME=David%20Winterbottom&SHIPTOSTREET=1%20Main%20Terrace&SHIPTOCITY=Wolverhampton&SHIPTOSTATE=West%20Midlands&SHIPTOZIP=W12%204LQ&SHIPTOCOUNTRYCODE=GB&SHIPTOCOUNTRYNAME=United%20Kingdom&ADDRESSSTATUS=Confirmed&CURRENCYCODE=GBP&AMT=6%2e99&SHIPPINGAMT=0%2e00&HANDLINGAMT=0%2e00&TAXAMT=0%2e00&INSURANCEAMT=0%2e00&SHIPDISCAMT=0%2e00'

    def test_token_is_extracted(self):
        self.assertEqual(self.token, self.txn.token)

    def test_is_successful(self):
        self.assertTrue(self.txn.is_successful)

    def test_ack(self):
        self.assertEqual('Success', self.txn.ack)

    def test_amount_is_saved(self):
        self.assertEqual(D('6.99'), self.txn.amount)

    def test_currency_is_saved(self):
        self.assertEqual('GBP', self.txn.currency)

    def test_correlation_id_is_saved(self):
        self.assertEqual('83bda082c24d4', self.txn.correlation_id)

    def test_context(self):
        ctx = self.txn.context
        values = [
            ('ACK', ['Success']),
            ('LASTNAME', ['Winterbottom']),
        ]
        for k, v in values:
            self.assertEqual(v, ctx[k])