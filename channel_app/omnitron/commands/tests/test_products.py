from unittest.mock import MagicMock, patch
from omnisdk.base_client import BaseClient
from omnisdk.omnitron.endpoints import (
    ChannelBatchRequestEndpoint,
    ChannelCategoryTreeEndpoint,
    ChannelIntegrationActionEndpoint,
    ChannelProductCategoryEndpoint,
    ChannelProductEndpoint,
    ChannelProductStockEndpoint, 
    ChannelExtraProductStockEndpoint, 
    ChannelExtraProductPriceEndpoint
)
from omnisdk.omnitron.models import ChannelAttributeConfig, ProductStock

from channel_app.core.commands import OmnitronCommandInterface
from channel_app.core.tests import BaseTestCaseMixin
from channel_app.omnitron.commands.batch_requests import GetBatchRequests
from channel_app.omnitron.commands.product_prices import GetProductStocksFromProductPrices
from channel_app.omnitron.commands.product_stocks import (
    GetInsertedProductStocks,
    GetProductPricesFromProductStocks,
    GetUpdatedProductStocks,
    GetUpdatedProductStocksFromExtraStockList, 
    GetInsertedProductStocksFromExtraStockList
)
from channel_app.omnitron.commands.products import (
    GetDeletedProducts,
    GetInsertedProducts,
    GetUpdatedProducts,
    Product,
    GetMappedProducts,
    GetProductPrices,
    GetProductStocks,
    GetProductCategoryNodes,
    GetProductCategoryNodesWithIntegrationAction,
)
from channel_app.omnitron.constants import (
    BatchRequestStatus,
    ContentType,
    FailedReasonType
)


class TestGetInsertedProducts(BaseTestCaseMixin):
    """
    Test case for GetInsertedProducts
    
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetInsertedProducts
    """

    def setUp(self) -> None:
        self.get_inserted_products = GetInsertedProducts(
            integration=self.mock_integration
        )
        self.sample_products = [
            Product(name='test', failed_reason_type=None),
            Product(name='test2', failed_reason_type='error')
        ]
        self.limit = 1

    @patch.object(GetInsertedProducts, 'get_products')
    def test_get_data(self, mock_get_products):
        mock_get_products.return_value = [self.sample_products[0]]
        self.get_inserted_products.BATCH_SIZE = self.limit

        products = self.get_inserted_products.get_data()

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, 'test')
        mock_get_products.assert_called_once_with(limit=self.limit)

    @patch.object(GetInsertedProducts, 'get_products')
    def test_get_data_with_limit_in_objects_dict(self, mock_get_products):
        mock_get_products.return_value = [self.sample_products[0]]
        self.get_inserted_products.objects = {'limit': self.limit}

        products = self.get_inserted_products.get_data()

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, 'test')
        mock_get_products.assert_called_once_with(limit=self.limit)

    def test_update_state_property(self):
        self.assertEqual(
            self.get_inserted_products.update_state,
            BatchRequestStatus.commit
        )

    def test_validated_data(self):
        validated_products = self.get_inserted_products.validated_data(
            self.sample_products
        )

        self.assertIn(self.sample_products[0], validated_products)
        self.assertNotIn(self.sample_products[1], validated_products)

    @patch('channel_app.core.clients.OmnitronApiClient')
    @patch.object(BaseClient, 'get_instance')
    @patch.object(GetInsertedProducts, 'update_batch_request')
    @patch.object(GetInsertedProducts, 'create_batch_objects')
    @patch.object(ChannelProductEndpoint, 'list')
    def test_get_products(
        self,
        mock_list,
        mock_create_batch_objects,
        mock_update_batch_request,
        mock_get_instance,
        mock_omnitron_api_client,
    ):
        mock_list.return_value = self.sample_products

        products = self.get_inserted_products.get_products(
            limit=self.limit + 1
        )

        self.assertEqual(len(products), 2)
        self.assertEqual(products[0].name, 'test')
        self.assertEqual(products[1].name, 'test2')


class TestGetUpdatedProducts(BaseTestCaseMixin):
    """
    Test case for GetUpdatedProducts
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetUpdatedProducts
    """

    def setUp(self):
        self.get_inserted_products = GetInsertedProducts(
            integration=self.mock_integration
        )
        self.get_updated_products = GetUpdatedProducts(
            integration=self.mock_integration
        )
        self.sample_products = [
            Product(
                pk=1,
                name='test',
                failed_reason_type=None,
                modified_date='2021-01-01T00:00:00Z',
                integration_action=MagicMock()
            ),
            Product(
                pk=2,
                name='test2',
                failed_reason_type='error',
                modified_date='2021-01-01T00:00:00Z',
                integration_action=MagicMock()
            )
        ]

    @patch.object(GetInsertedProducts, 'get_products')
    @patch.object(GetUpdatedProducts, 'get_integration_actions')
    def test_get_data(self, mock_get_integration_actions, mock_get_products):
        mock_get_integration_actions.return_value = self.sample_products
        mock_get_products.return_value = [self.sample_products[0]]
        products = self.get_updated_products.get_data()

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, 'test')

    @patch('channel_app.core.clients.OmnitronApiClient')
    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelIntegrationActionEndpoint, 'list')
    def test_get_integration_actions(
        self,
        mock_list,
        mock_get_instance,
        mock_omnitron_api_client
    ):
        example_response = MagicMock()
        example_response.json.return_value = [
            {
                'id': 1,
                'channel': 1,
                'content_type': 'product',
                'remote_id': 1,
                'object_id': 1,
            },
            {
                'id': 2,
                'channel': 1,
                'content_type': 'product',
                'remote_id': 2,
                'object_id': 2,
            }
        ]

        with patch.object(
            ChannelIntegrationActionEndpoint,
            '__new__',
            return_value=example_response,
        ):
            products = self.get_updated_products.get_integration_actions(
                self.sample_products
            )

        self.assertEqual(len(products), 2)

    def test_get_integration_actions_without_product(self):
        products = self.get_updated_products.get_integration_actions([])
        self.assertEqual(products, [])


class TestGetInsertedOrUpdatedProducts(
    TestGetInsertedProducts,
    BaseTestCaseMixin
):
    """
    Test case for GetInsertedOrUpdatedProducts
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetInsertedOrUpdatedProducts
    """

    def setUp(self) -> None:
        self.get_inserted_products = GetInsertedProducts(
            integration=self.mock_integration
        )
        self.get_inserted_products.path = "inserts_or_updates"
        return super().setUp()


class TestGetDeletedProducts(BaseTestCaseMixin):
    """
    Test case for GetDeletedProducts
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetDeletedProducts
    """

    def setUp(self) -> None:
        self.get_deleted_products = GetDeletedProducts(
            integration=self.mock_integration
        )
        self.products = [
            {
                "pk": 23,
                "channel": 3,
                "content_type": {
                    "id": 1,
                    "app_label": "products",
                    "model": "product"
                },
                "object_id": 1,
                "remote_id": None,
                "version_date": "2023-11-07T08:58:16.079727Z",
                "state": {},
                "modified_date": "2023-11-08T09:11:56.919937Z",
                "local_batch_id": "7c43e5fb-32be-4a18-a6fa-539c9d2485ee",
                "status": "processing",
                "created_date": "2023-11-08T09:11:56.919929Z"
            }
        ]

    @patch.object(GetDeletedProducts, 'get_deleted_products_ia')
    def test_get_data(self, mock_get_deleted_products_ia):
        mock_get_deleted_products_ia.return_value = self.products
        products = self.get_deleted_products.get_data()
        self.assertEqual(len(products), 1)

        product = products[0]
        self.assertEqual(product.get('pk'), 23)

    @patch('channel_app.core.clients.OmnitronApiClient')
    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelIntegrationActionEndpoint, '_list')
    def test_get_deleted_products_ia(
        self,
        mock_list,
        mock_get_instance,
        mock_omnitron_api_client
    ):
        example_response = MagicMock()
        example_response.json.return_value = self.products
        mock_list.return_value = example_response
        products_ia = self.get_deleted_products.get_deleted_products_ia()
        self.assertEqual(len(products_ia), 1)

        product = products_ia[0].get_parameters()
        self.assertEqual(product.get('pk'), 23)


class TestGetMappedProducts(BaseTestCaseMixin):
    """
    Test case for GetMappedProducts
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetMappedProducts
    """

    def setUp(self) -> None:
        self.get_mapped_products = GetMappedProducts(
            integration=self.mock_integration
        )
        self.sample_products = [
            Product(
                pk=1,
                name='test',
                failed_reason_type=None,
                modified_date='2021-01-01T00:00:00Z'
            ),
            Product(
                pk=2,
                name='test2',
                failed_reason_type='error',
                modified_date='2021-01-01T00:00:00Z'
            )
        ]

    @patch.object(GetMappedProducts, 'get_mapping')
    def test_get_data(self, mock_get_mapping):
        mock_get_mapping.return_value = self.sample_products
        result = self.get_mapped_products.get_data()
        self.assertEqual(len(result), 2)

    @patch.object(GetMappedProducts, 'check_product')
    def test_validated_data(self, mock_check_product):
        data = self.sample_products
        self.get_mapped_products.validated_data(data)
        self.assertEqual(mock_check_product.call_count, 2)

    @patch.object(GetMappedProducts, 'get_attribute_config_list')
    @patch.object(GetMappedProducts, 'update_and_check_product')
    def test_check_product_gets_attribute_config_list(
        self,
        mock_update_and_check_product,
        mock_get_attribute_config_list
    ):
        product = Product()
        product.mapped_attributes = MagicMock()
        product.mapped_attributes.attribute_set_id = 1
        product.mapped_attributes.mapped_attribute_values = {
            "1": {
                "value": "test"
            }
        }
        mock_get_attribute_config_list.return_value = [
            ChannelAttributeConfig()
        ]
        self.get_mapped_products.check_product(
            product,
            {}
        )
        mock_get_attribute_config_list.assert_called_once()

    @patch.object(GetMappedProducts, 'check_attribute_value_defined')
    @patch.object(GetMappedProducts, 'check_required')
    def test_update_and_check_product_checks_attribute_value_and_required(
        self,
        mock_check_required,
        mock_check_attribute_value_defined
    ):
        product = Product()
        product.mapped_attributes = MagicMock()
        product.mapped_attributes.mapped_attribute_values = {}
        config = ChannelAttributeConfig()
        config.attribute_remote_id = 1
        config.is_required = True
        config.is_variant = True
        config.is_custom = True
        config.is_meta = True
        config.attribute = {
            "pk": 1,
            "name": "test",
        }
        result = self.get_mapped_products.update_and_check_product(
            config,
            product
        )
        self.assertFalse(result)

    @patch.object(GetMappedProducts, 'check_attribute_value_defined')
    @patch.object(GetMappedProducts, 'check_required')
    def test_update_and_check_product(
        self,
        mock_check_required,
        mock_check_attribute_value_defined
    ):
        product = Product()
        product.mapped_attributes = MagicMock()
        product.mapped_attributes.mapped_attribute_values = {
            "1": {
                "value": "test"
            }
        }
        config = ChannelAttributeConfig()
        config.attribute_remote_id = 1
        config.is_required = True
        config.is_variant = True
        config.is_custom = True
        config.is_meta = True
        config.attribute = {
            "pk": 1,
            "name": "test",
        }
        result = self.get_mapped_products.update_and_check_product(
            config,
            product
        )
        self.assertTrue(result)

    @patch.object(GetMappedProducts, 'get_attribute_config_list')
    def test_get_attribute_config_list_returns_configs_data(
        self,
        mock_get_attribute_config_list
    ):
        config = ChannelAttributeConfig()
        mock_get_attribute_config_list.return_value = [
            config
        ]
        result = self.get_mapped_products.get_attribute_config_list(
            {"attribute_set": 1, "limit": 10}
        )
        self.assertEqual(result, [config])

    def test_check_attribute_value_defined_raises_exception_when_mapped_value_not_defined(self):
        mapped_attributes_obj = MagicMock()
        mapped_attributes_obj.mapped_attributes = {"name": "value"}
        mapped_attributes_obj.mapped_attribute_values = {}
        config = ChannelAttributeConfig()
        config.attribute = {"pk": 1, "name": "name"}
        config.attribute_set = {"pk": 1, "name": "name"}
        config.is_custom = False
        with self.assertRaises(Exception):
            self.get_mapped_products.check_attribute_value_defined(
                config,
                mapped_attributes_obj
            )

    def test_check_required_raises_exception_when_required_attribute_missing(self):
        product = Product()
        product.sku = "sku"
        self.get_mapped_products.integration = MagicMock()
        self.get_mapped_products.integration.channel_id = 1
        mapped_attributes = {}
        config = ChannelAttributeConfig()
        config.attribute = {"name": "name"}
        config.is_required = True
        with self.assertRaises(Exception):
            self.get_mapped_products.check_required(
                product,
                config,
                mapped_attributes
            )

    @patch.object(GetMappedProducts, 'get_mapping')
    def test_get_mapping_returns_mapped_products(self, mock_get_mapping):
        product = Product()
        mock_get_mapping.return_value = [product]
        result = self.get_mapped_products.get_mapping([product])
        self.assertEqual(result, [product])

    @patch.object(GetMappedProducts, 'get_mapping')
    def test_get_mapping_returns_empty_list_when_no_products(self, mock_get_mapping):
        mock_get_mapping.return_value = []
        result = self.get_mapped_products.get_mapping([])
        self.assertEqual(result, [])


class TestGetMappedProductsWithOutCommit(TestGetMappedProducts):
    pass


class TestGetProductPrices(BaseTestCaseMixin):
    """
    Test case for GetProductPrices
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetProductPrices
    """

    def setUp(self) -> None:
        self.get_product_prices = GetProductPrices(
            integration=self.mock_integration
        )

    @patch.object(BaseClient, 'get_instance')
    @patch.object(GetProductPrices, 'get_prices')
    def test_successful_product_price_retrieval(
        self,
        mock_get_instance,
        mock_get_prices
    ):
        products = [Product(pk=i, productprice=10) for i in range(1, 6)]
        self.get_product_prices.objects = products

        result = self.get_product_prices.get_data()
        self.assertEqual(result, products)

    @patch.object(GetProductPrices, 'get_prices')
    @patch.object(BaseClient, 'get_instance')
    def test_product_price_retrieval_with_successful_get_product_price(
        self,
        mock_get_instance,
        mock_get_prices
    ):
        products = [Product(pk=i) for i in range(1, 6)]

        price_list = []
        for product in products:
            price = MagicMock()
            price.product = product.pk
            price_list.append(price)

        mock_get_prices.return_value = price_list
        result = self.get_product_prices.get_product_price(products)
        self.assertEqual(result, products)

    @patch.object(GetProductPrices, 'get_prices')
    @patch.object(BaseClient, 'get_instance')
    def test_product_price_retrieval_with_failed_get_product_price(
        self,
        mock_get_instance,
        mock_get_prices
    ):
        products = [Product(pk=i, product_price=0) for i in range(1, 6)]

        price_list = []
        for product in products:
            price = MagicMock()
            price.product = product.pk

            if len(price_list) < len(products) - 1:
                price_list.append(price)

        mock_get_prices.return_value = price_list
        result = self.get_product_prices.get_product_price(products)
        self.assertFalse(hasattr(result[-1], 'productprice'))


class TestGetProductPricesWithOutCommit(TestGetProductPrices):
    pass


class TestGetProductStocks(BaseTestCaseMixin):
    """
    Test case for GetProductStocks
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetProductStocks
    """

    def setUp(self) -> None:
        self.get_product_stocks = GetProductStocks(
            integration=self.mock_integration
        )
        self.sample_products = [
            Product(
                pk=1,
                name='test',
                failed_reason_type=None,
                productstock=10,
                modified_date='2021-01-01T00:00:00Z'
            ),
            Product(
                pk=2,
                name='test2',
                failed_reason_type='error',
                productstock=15,
                modified_date='2021-01-01T00:00:00Z'
            )
        ]

    @patch.object(BaseClient, 'get_instance')
    @patch.object(GetProductStocks, 'get_stocks')
    def test_get_data(
        self,
        mock_get_stocks,
        mock_get_instance
    ):
        mock_get_stocks.return_value = []
        self.get_product_stocks.objects = self.sample_products
        result = self.get_product_stocks.get_data()
        self.assertEqual(len(result), 2)

    @patch.object(GetProductStocks, 'create_batch_objects')
    @patch.object(GetProductStocks, 'create_integration_actions')
    @patch.object(GetProductStocks, 'update_batch_request')
    def test_normalize_response(
        self,
        mock_update_batch_request,
        mock_create_integration_actions,
        mock_create_batch_objects
    ):
        data = self.sample_products
        response = MagicMock()
        response.json.return_value = []
        self.get_product_stocks.failed_object_list = []
        result = self.get_product_stocks.normalize_response(data, response)
        self.assertEqual(result, data)

    @patch.object(GetProductStocks, 'create_batch_objects')
    def test_create_integration_actions(self, mock_create_batch_objects):
        data = self.sample_products
        object_list = []
        self.get_product_stocks.create_integration_actions(data, object_list)
        self.assertEqual(mock_create_batch_objects.call_count, 1)

    @patch.object(BaseClient, 'get_instance')
    @patch.object(GetProductStocks, 'get_stocks')
    def test_get_product_stock(self, mock_get_stocks, mock_get_instance):
        products = self.sample_products
        mock_get_stocks.return_value = []
        result = self.get_product_stocks.get_product_stock(products)
        self.assertEqual(result, products)
        self.assertEqual(len(self.get_product_stocks.failed_object_list), 1)

    @patch.object(BaseClient, 'get_instance')
    @patch.object(GetProductStocks, 'get_stocks')
    def test_get_product_stock_with_failed_product(
        self,
        mock_get_stocks,
        mock_get_instance
    ):
        products = self.sample_products
        products[1].failed_reason_type = FailedReasonType.channel_app.value
        mock_get_stocks.return_value = []
        result = self.get_product_stocks.get_product_stock(products)
        self.assertEqual(result, products)
        self.assertEqual(
            len(self.get_product_stocks.failed_object_list),
            1
        )
        self.assertEqual(
            self.get_product_stocks.failed_object_list[0][0],
            products[0]
        )
        self.assertEqual(
            self.get_product_stocks.failed_object_list[0][1],
            ContentType.product.value
        )
        self.assertEqual(
            self.get_product_stocks.failed_object_list[0][2],
            "StockNotFound"
        )

    @patch.object(BaseClient, 'get_instance')
    @patch.object(GetProductStocks, 'get_stocks')
    def test_get_product_stock_with_stock_not_found(
        self,
        mock_get_stocks,
        mock_get_instance
    ):
        products = self.sample_products
        mock_get_stocks.return_value = []
        result = self.get_product_stocks.get_product_stock(products)
        self.assertEqual(result, products)
        self.assertEqual(
            len(self.get_product_stocks.failed_object_list),
            1
        )
        self.assertEqual(
            self.get_product_stocks.failed_object_list[0][0],
            products[0]
        )
        self.assertEqual(
            self.get_product_stocks.failed_object_list[0][1],
            ContentType.product.value
        )
        self.assertEqual(
            self.get_product_stocks.failed_object_list[0][2],
            "StockNotFound"
        )

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelProductStockEndpoint, '_list')
    def test_get_stocks(self, mock_endpoint, mock_get_instance):
        example_response = MagicMock()
        example_response.json.return_value = [
            {
                'id': 1,
                'product': 1,
                'stock': 1,
            },
            {
                'id': 2,
                'product': 2,
                'stock': 1,
            }
        ]
        mock_endpoint.return_value = example_response
        result = self.get_product_stocks.get_stocks(
            chunk=["1", "2"],
            endpoint=ChannelProductStockEndpoint()
        )
        self.assertEqual(len(result), 2)


class TestGetProductStocksWithOutCommit(TestGetProductStocks):
    pass


class TestGetProductCategoryNodes(BaseTestCaseMixin):
    """
    Test case for GetProductCategoryNodes
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetProductCategoryNodes
    """

    def setUp(self) -> None:
        self.get_product_category_nodes = GetProductCategoryNodes(
            integration=self.mock_integration
        )
        self.sample_products = [
            Product(pk=1),
            Product(pk=2)
        ]

    @patch.object(GetProductCategoryNodes, 'get_product_category')
    def test_get_data(self, mock_get_product_category):
        self.get_product_category_nodes.objects = self.sample_products
        mock_get_product_category.return_value = self.sample_products
        result = self.get_product_category_nodes.get_data()
        self.assertEqual(len(result), 2)
        self.assertEqual(result, self.sample_products)
        mock_get_product_category.assert_called_once()

    @patch.object(GetProductCategoryNodes, 'create_batch_objects')
    @patch.object(GetProductCategoryNodes, 'update_batch_request')
    def test_normalize_response(
        self,
        mock_update_batch_request,
        mock_create_batch_objects
    ):
        data = self.sample_products
        response = MagicMock()
        self.get_product_category_nodes.failed_object_list = [
            (
                self.sample_products[0],
                ContentType.product.value,
                "ProductCategoryNotFound"
            )
        ]
        self.get_product_category_nodes.normalize_response(data, response)
        mock_create_batch_objects.assert_called_once_with(
            data=[self.sample_products[0]],
            content_type=ContentType.product.value,
        )
        mock_update_batch_request.assert_called_once_with(
            mock_create_batch_objects.return_value
        )

    def test_get_product_category(self):
        products = self.sample_products
        category_tree_id = 1
        category_tree = MagicMock()
        category_tree.category_root = {"path": "/root/category"}
        category_tree_endpoint = MagicMock()
        category_tree_endpoint.retrieve.return_value = category_tree
        product_category_endpoint = MagicMock()
        product_category_endpoint.list.return_value = [
            MagicMock(
                category={
                    "path": "/root/category/category1"
                }
            ),
            MagicMock(
                category={
                    "path": "/root/category/category2"
                }
            ),
        ]
        product_category_endpoint.iterator = [
            [MagicMock(
                category={
                    "path": "/root/category/category1"
                }
            )],
            [MagicMock(
                category={
                    "path": "/root/category/category2"
                }
            )],
        ]

        with patch.object(
                ChannelCategoryTreeEndpoint,
                '__new__',
                return_value=category_tree_endpoint,
        ), patch.object(
            ChannelProductCategoryEndpoint,
            '__new__',
            return_value=product_category_endpoint,
        ):
            self.get_product_category_nodes.get_product_category(products)

        self.assertEqual(len(products), 2)
        self.assertEqual(
            self.get_product_category_nodes.failed_object_list,
            []
        )

    def test_get_product_category_with_empty_products(self):
        products = []
        result = self.get_product_category_nodes.get_product_category(products)
        self.assertEqual(result, [])
        self.assertEqual(self.get_product_category_nodes.failed_object_list, [])


class TestGetProductCategoryNodesWithIntegrationAction(TestGetProductCategoryNodes):
    """
    Test case for GetProductCategoryNodes
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetProductCategoryNodesWithIntegrationAction
    """

    def setUp(self) -> None:
        self.get_product_category_nodes = GetProductCategoryNodesWithIntegrationAction(
            integration=self.mock_integration
        )
        self.sample_products = [
            Product(
                pk=1,
                category_nodes=[
                    {
                        'pk': 1,
                        'path': '/root/category/category1'
                    }
                ]
            ),
            Product(
                pk=2,
                category_nodes=[
                    {
                        'pk': 2,
                        'path': '/root/category/category2'
                    }
                ]
            )
        ]

    @patch.object(BaseClient, 'get_instance')
    @patch.object(
        GetProductCategoryNodesWithIntegrationAction,
        'get_data'
    )
    @patch.object(
        GetProductCategoryNodesWithIntegrationAction,
        'get_category_node_integration_action'
    )
    def test_get_data(
        self,
        mock_get_category_node_integration_action,
        mock_get_data,
        mock_get_instance
    ):
        self.get_product_category_nodes.objects = self.sample_products
        mock_get_data.return_value = self.sample_products
        result = self.get_product_category_nodes.get_data()
        self.assertEqual(len(result), 2)

    @patch.object(
        GetProductCategoryNodesWithIntegrationAction,
        'get_category_node_integration_action'
    )
    def test_get_category_node_integration_action(
        self,
        mock_get_category_node_integration_action
    ):
        mock_get_category_node_integration_action.return_value = None
        result = self.get_product_category_nodes.get_category_node_integration_action(
            self.sample_products
        )
        self.assertIsNone(result)

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelIntegrationActionEndpoint, 'list')
    def test_get_category_node_integration_action_with_products(
        self,
        mock_endpoint,
        mock_get_instance
    ):
        integration_action_endpoint = MagicMock()
        integration_action_endpoint.list.return_value = [
            MagicMock(
                channel=1,
                object_id=1
            ),
        ]
        integration_action_endpoint.iterator = [
            [MagicMock(
                channel=1,
                object_id=1
            )],
        ]
        mock_endpoint.return_value = integration_action_endpoint

        with patch.object(
                ChannelIntegrationActionEndpoint,
                '__new__',
                return_value=integration_action_endpoint,
                channel_id=1
        ):
            result = self.get_product_category_nodes.get_category_node_integration_action(
                self.sample_products
            )

        self.assertEqual(len(result), 2)


class TestGetBatchRequests(BaseTestCaseMixin):
    """
    Test case for GetBatchRequests
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetBatchRequests
    """

    def setUp(self):
        self.get_batch_requests = GetBatchRequests(
            integration=self.mock_integration,
            params={"limit": 1}
        )

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelBatchRequestEndpoint, 'list')
    def test_get_data(self, mock_list, mock_get_instance):
        self.get_batch_requests.params = {
            "limit": 1
        }
        mock_list.return_value = [
            {
                "pk": 22,
                "channel": 6,
                "local_batch_id": "89bb31b0-6700-4a9d-8bae-308ac938649c",
                "remote_batch_id": "028b8e66-2a4c-45b5-912f-9ab90036c78a",
                "content_type": "product",
                "status": "sent_to_remote"
            }
        ]

        data = self.get_batch_requests.get_data()

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("pk"), 22)
        self.assertEqual(data[0].get("channel"), 6)
        self.assertEqual(data[0].get("local_batch_id"), "89bb31b0-6700-4a9d-8bae-308ac938649c")
        self.assertEqual(data[0].get("remote_batch_id"), "028b8e66-2a4c-45b5-912f-9ab90036c78a")
        self.assertEqual(data[0].get("content_type"), "product")
        self.assertEqual(data[0].get("status"), "sent_to_remote")
        mock_list.assert_called_once()


class TestGetUpdatedProductStocks(BaseTestCaseMixin):
    """
    Test case for GetUpdatedProductStocks
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetUpdatedProductStocks
    """

    def setUp(self) -> None:
        self.get_updated_product_stocks = GetUpdatedProductStocks(
            integration=self.mock_integration
        )
        self.sample_stocks = [
            ProductStock(
                pk=3,
                product=1,
                stock=0,
                stock_list=4,
                unit_type='qty',
                extra_field={},
                sold_quantity_unreported=0,
                modified_date='2023-12-19T08:38:48.476005Z',
                created_date='2023-12-19T08:38:48.475992Z'
            ),
            ProductStock(
                pk=4,
                product=2,
                stock=0,
                stock_list=4,
                unit_type='qty',
                extra_field={},
                sold_quantity_unreported=0,
                modified_date='2023-12-19T08:38:48.476005Z',
                created_date='2023-12-19T08:38:48.475992Z'
            )
        ]

    @patch.object(BaseClient, 'get_instance')
    @patch.object(GetUpdatedProductStocks, 'get_product_stocks')
    @patch.object(GetUpdatedProductStocks, 'get_stocks_with_available')
    def test_get_data(
        self,
        mock_get_stocks_with_available,
        mock_get_product_stocks,
        mock_get_instance
    ):
        mock_get_product_stocks.return_value = self.sample_stocks
        mock_get_stocks_with_available.return_value = self.sample_stocks

        stocks = self.get_updated_product_stocks.get_data()

        self.assertEqual(len(stocks), 2)
        self.assertEqual(stocks[0].pk, self.sample_stocks[0].pk)
        self.assertEqual(stocks[1].pk, self.sample_stocks[1].pk)
        mock_get_product_stocks.assert_called_once()
        mock_get_stocks_with_available.assert_called_once()

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelProductStockEndpoint, 'list')
    @patch.object(OmnitronCommandInterface, 'create_batch_objects')
    @patch.object(OmnitronCommandInterface, 'update_batch_request')
    def test_get_product_stocks(
        self,
        mock_update_batch_request,
        mock_create_batch_objects,
        mock_endpoint,
        mock_get_instance
    ):
        mock_endpoint.return_value = [
            {
                'pk': 3,
                'product': 1,
                'stock': 0,
                'stock_list': 4,
                'unit_type': 'qty',
                'extra_field': {},
                'sold_quantity_unreported': 0,
                'modified_date': '2023-12-19T08:38:48.476005Z',
                'created_date': '2023-12-19T08:38:48.475992Z'
            },
            {
                'pk': 4,
                'product': 2,
                'stock': 0,
                'stock_list': 4,
                'unit_type': 'qty',
                'extra_field': {},
                'sold_quantity_unreported': 0,
                'modified_date': '2023-12-19T08:38:48.476005Z',
                'created_date': '2023-12-19T08:38:48.475992Z'
            }
        ]
        mock_create_batch_objects.return_value = [
            {
                'pk': 3,
                'failed_reason_type': None,
                'remote_id': 3,
                'version_date': '2023-12-19T08:38:48.476005Z',
                'content_type': 'product_stock',
            },
            {
                'pk': 4,
                'failed_reason_type': None,
                'remote_id': 4,
                'version_date': '2023-12-19T08:38:48.476005Z',
                'content_type': 'product_stock',
            }
        ]

        stocks = self.get_updated_product_stocks.get_product_stocks()
        self.assertEqual(len(stocks), 2)
        self.assertEqual(stocks[0].get('pk'), 3)
        self.assertEqual(stocks[1].get('pk'), 4)
        mock_endpoint.assert_called_once()
        mock_create_batch_objects.assert_called_once()
        mock_update_batch_request.assert_called_once()

    @patch.object(BaseClient, 'get_instance')
    def test_get_stocks_with_available(
        self,
        mock_get_instance
    ):
        mock_endpoint = MagicMock(channel_id=1)
        mock_endpoint.list.return_value = [
            MagicMock(
                pk=1,
                channel=2,
                content_type=ContentType.product_stock.value,
                object_id=self.sample_stocks[0].pk,
                remote_id=None,
                version_date="2023-12-28T10:28:17.186730Z",
                state={},
                modified_date="2023-12-28T10:28:17.187032Z",
                local_batch_id=None,
                status=None,
                created_date="2023-12-28T10:28:17.187014Z"
            ),
            MagicMock(
                pk=2,
                channel=2,
                content_type=ContentType.product_stock.value,
                object_id=self.sample_stocks[1].pk,
                remote_id=None,
                version_date="2023-12-28T10:28:17.186730Z",
                state={},
                modified_date="2023-12-28T10:28:17.187032Z",
                local_batch_id=None,
                status=None,
                created_date="2023-12-28T10:28:17.187014Z"
            )
        ]

        mock_endpoint.iterator = [
            [
                MagicMock(
                    pk=1,
                    channel=2,
                    content_type=ContentType.product_stock.value,
                    object_id=self.sample_stocks[0].pk,
                    remote_id=None,
                    version_date="2023-12-28T10:28:17.186730Z",
                    state={},
                    modified_date="2023-12-28T10:28:17.187032Z",
                    local_batch_id=None,
                    status=None,
                    created_date="2023-12-28T10:28:17.187014Z"
                )
            ],
            [
                MagicMock(
                    pk=2,
                    channel=2,
                    content_type=ContentType.product_stock.value,
                    object_id=self.sample_stocks[1].pk,
                    remote_id=None,
                    version_date="2023-12-28T10:28:17.186730Z",
                    state={},
                    modified_date="2023-12-28T10:28:17.187032Z",
                    local_batch_id=None,
                    status=None,
                    created_date="2023-12-28T10:28:17.187014Z"
                )
            ]
        ]

        with patch.object(
                ChannelIntegrationActionEndpoint,
                '__new__',
                return_value=mock_endpoint,
        ):
            stocks = self.get_updated_product_stocks.get_stocks_with_available(
                self.sample_stocks
            )

        self.assertEqual(len(stocks), 2)
        self.assertEqual(stocks[0].pk, self.sample_stocks[0].pk)
        self.assertEqual(stocks[1].pk, self.sample_stocks[1].pk)


class TestGetInsertedProductStocks(BaseTestCaseMixin):
    """
    Test case for GetInsertedProductStocks
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetInsertedProductStocks
    """

    def setUp(self):
        self.get_inserted_product_stocks = GetInsertedProductStocks(
            integration=self.mock_integration
        )
        self.sample_stocks = [
            ProductStock(
                pk=3,
                product=1,
                stock=0,
                stock_list=4,
                unit_type='qty',
                extra_field={},
                sold_quantity_unreported=0,
                modified_date='2023-12-19T08:38:48.476005Z',
                created_date='2023-12-19T08:38:48.475992Z'
            ),
            ProductStock(
                pk=4,
                product=2,
                stock=0,
                stock_list=4,
                unit_type='qty',
                extra_field={},
                sold_quantity_unreported=0,
                modified_date='2023-12-19T08:38:48.476005Z',
                created_date='2023-12-19T08:38:48.475992Z'
            )
        ]

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelIntegrationActionEndpoint, 'list')
    def test_get_stocks_with_available(
        self,
        mock_endpoint,
        mock_get_instance
    ):
        example_response = MagicMock()
        example_response.return_value = [
            {
                "pk": 1,
                "channel": 2,
                "content_type": {
                    "id": 119,
                    "app_label": "search",
                    "model": "productstock"
                },
                "object_id": self.sample_stocks[0].pk,
                "remote_id": None,
                "version_date": "2023-12-28T10:28:17.186730Z",
                "state": {},
                "modified_date": "2023-12-28T10:28:17.187032Z",
                "local_batch_id": None,
                "status": None,
                "created_date": "2023-12-28T10:28:17.187014Z"
            },
            {
                "pk": 2,
                "channel": 2,
                "content_type": {
                    "id": 119,
                    "app_label": "search",
                    "model": "productstock"
                },
                "object_id": self.sample_stocks[1].pk,
                "remote_id": None,
                "version_date": "2023-12-28T10:28:17.186730Z",
                "state": {},
                "modified_date": "2023-12-28T10:28:17.187032Z",
                "local_batch_id": None,
                "status": None,
                "created_date": "2023-12-28T10:28:17.187014Z"
            }
        ]

        with patch.object(
                ChannelIntegrationActionEndpoint,
                '__new__',
                return_value=example_response,
        ):
            stocks = self.get_inserted_product_stocks.get_stocks_with_available(
                self.sample_stocks
            )

        self.assertEqual(len(stocks), 2)
        self.assertEqual(stocks[0].pk, self.sample_stocks[0].pk)
        self.assertEqual(stocks[1].pk, self.sample_stocks[1].pk)


class TestGetUpdatedProductStocksFromExtraStockList(BaseTestCaseMixin):
    """
    Test case for GetupdatedProductStocksFromExtraStockList
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetUpdatedProductStocksFromExtraStockList
    """

    def setUp(self) -> None:
        self.get_updated_product_stocks_from_extra_stock_list = GetUpdatedProductStocksFromExtraStockList(
            integration=self.mock_integration
        )
        self.sample_stocks = [
            ProductStock(
                pk=3,
                product=1,
                stock=0,
                stock_list=4,
                unit_type='qty',
                extra_field={},
                sold_quantity_unreported=0,
                modified_date='2023-12-19T08:38:48.476005Z',
                created_date='2023-12-19T08:38:48.475992Z'
            ),
            ProductStock(
                pk=4,
                product=2,
                stock=0,
                stock_list=4,
                unit_type='qty',
                extra_field={},
                sold_quantity_unreported=0,
                modified_date='2023-12-19T08:38:48.476005Z',
                created_date='2023-12-19T08:38:48.475992Z'
            )
        ]
        self.objects = self.sample_stocks
        self.stock_list_id = 4

    @patch.object(
        BaseClient, 
        'get_instance'
    )
    @patch.object(
        GetUpdatedProductStocksFromExtraStockList, 
        'get_product_stocks'
    )
    @patch.object(
        GetUpdatedProductStocksFromExtraStockList, 
        'get_integration_actions'
    )
    def test_get_data(
        self,
        mock_get_integration_actions,
        mock_get_product_stocks,
        mock_get_instance
    ):
        mock_get_integration_actions.return_value = self.sample_stocks
        mock_get_product_stocks.return_value = self.sample_stocks
        stocks = self.get_updated_product_stocks_from_extra_stock_list.get_data()

        self.assertEqual(len(stocks), 2)
        self.assertEqual(stocks[0].pk, self.sample_stocks[0].pk)
        self.assertEqual(stocks[1].pk, self.sample_stocks[1].pk)

    @patch.object(
        BaseClient, 
        'get_instance'
    )
    @patch.object(
        ChannelIntegrationActionEndpoint, 
        'list'
    )
    @patch.object(
        GetUpdatedProductStocksFromExtraStockList, 
        'create_batch_objects'
    )
    @patch.object(
        GetUpdatedProductStocksFromExtraStockList, 
        'update_batch_request'
    )
    def test_get_product_stocks(
        self,
        mock_update_batch_request,
        mock_create_batch_objects,
        mock_list,
        mock_get_instance
    ):
        self.get_updated_product_stocks_from_extra_stock_list.objects = self.objects
        self.get_updated_product_stocks_from_extra_stock_list.stock_list_id = self.stock_list_id

        mock_endpoint = MagicMock()
        mock_endpoint.list.return_value = [
            {
                'pk': 3,
                'product': 1,
                'stock': 0,
                'stock_list': 4,
                'unit_type': 'qty',
                'extra_field': {},
                'sold_quantity_unreported': 0,
                'modified_date': '2023-12-19T08:38:48.476005Z',
                'created_date': '2023-12-19T08:38:48.475992Z'
            },
            {
                'pk': 4,
                'product': 2,
                'stock': 0,
                'stock_list': 4,
                'unit_type': 'qty',
                'extra_field': {},
                'sold_quantity_unreported': 0,
                'modified_date': '2023-12-19T08:38:48.476005Z',
                'created_date': '2023-12-19T08:38:48.475992Z'
            }
        ]

        with patch.object(
            ChannelExtraProductStockEndpoint,
            '__new__',
            return_value=mock_endpoint
        ):
            stocks = self.get_updated_product_stocks_from_extra_stock_list.get_product_stocks()

        self.assertEqual(len(stocks), 2)
        self.assertEqual(stocks[0].get('pk'), 3)
        self.assertEqual(stocks[1].get('pk'), 4)

    def test_get_integration_actions_without_stocks(self):
        self.sample_stocks = []
        stocks = self.get_updated_product_stocks_from_extra_stock_list.get_integration_actions(
            self.sample_stocks
        )
        self.assertEqual(stocks, [])

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelIntegrationActionEndpoint, 'list')
    def test_get_integration_actions(
        self,
        mock_get_instance,
        mock_list
    ):
        mock_endpoint = MagicMock()
        mock_endpoint.list.return_value = [
            MagicMock(
                pk=1,
                channel=2,
                content_type=ContentType.product_stock.value,
                object_id=self.sample_stocks[0].pk,
                remote_id=None,
                version_date="2023-12-28T10:28:17.186730Z",
                state={},
                modified_date="2023-12-28T10:28:17.187032Z",
                local_batch_id=None,
                status=None,
                created_date="2023-12-28T10:28:17.187014Z"
            ),
            MagicMock(
                pk=2,
                channel=2,
                content_type=ContentType.product_stock.value,
                object_id=self.sample_stocks[1].pk,
                remote_id=None,
                version_date="2023-12-28T10:28:17.186730Z",
                state={},
                modified_date="2023-12-28T10:28:17.187032Z",
                local_batch_id=None,
                status=None,
                created_date="2023-12-28T10:28:17.187014Z"
            )
        ]
        mock_endpoint.iterator = [
            [
                MagicMock(
                    pk=1,
                    channel=2,
                    content_type=ContentType.product_stock.value,
                    object_id=self.sample_stocks[0].pk,
                    remote_id=None,
                    version_date="2023-12-28T10:28:17.186730Z",
                    state={},
                    modified_date="2023-12-28T10:28:17.187032Z",
                    local_batch_id=None,
                    status=None,
                    created_date="2023-12-28T10:28:17.187014Z"
                )
            ],
            [
                MagicMock(
                    pk=2,
                    channel=2,
                    content_type=ContentType.product_stock.value,
                    object_id=self.sample_stocks[1].pk,
                    remote_id=None,
                    version_date="2023-12-28T10:28:17.186730Z",
                    state={},
                    modified_date="2023-12-28T10:28:17.187032Z",
                    local_batch_id=None,
                    status=None,
                    created_date="2023-12-28T10:28:17.187014Z"
                )
            ]
        ]

        with patch.object(
            ChannelIntegrationActionEndpoint,
            '__new__',
            return_value=mock_endpoint
        ):
            stocks = self.get_updated_product_stocks_from_extra_stock_list.get_integration_actions(
                self.sample_stocks
            )

        self.assertEqual(len(stocks), 2)
        self.assertEqual(stocks[0].pk, self.sample_stocks[0].pk)
        self.assertEqual(stocks[1].pk, self.sample_stocks[1].pk)


class TestGetProductPricesFromProductStocks(BaseTestCaseMixin):
    """
    Test case for GetProductPricesFromProductStocks
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetProductPricesFromProductStocks
    """

    def setUp(self) -> None:
        self.get_product_prices_from_product_stocks = GetProductPricesFromProductStocks(
            integration=self.mock_integration
        )
        self.sample_stocks = [
            ProductStock(
                pk=3,
                product=1,
                stock=0,
                stock_list=4,
                unit_type='qty',
                extra_field={},
                sold_quantity_unreported=0,
                modified_date='2023-12-19T08:38:48.476005Z',
                created_date='2023-12-19T08:38:48.475992Z',
                productprice=10
            ),
            ProductStock(
                pk=4,
                product=2,
                stock=0,
                stock_list=4,
                unit_type='qty',
                extra_field={},
                sold_quantity_unreported=0,
                modified_date='2023-12-19T08:38:48.476005Z',
                created_date='2023-12-19T08:38:48.475992Z',
                productprice=10
            )
        ]

    @patch.object(BaseClient, 'get_instance')
    @patch.object(GetProductPricesFromProductStocks, 'get_product_price')
    def test_get_data(
        self,
        mock_get_product_price,
        mock_get_instance
    ):
        self.get_product_prices_from_product_stocks.objects = self.sample_stocks
        stocks = self.get_product_prices_from_product_stocks.get_data()
        self.assertEqual(len(stocks), 2)
        self.assertEqual(stocks[0].pk, self.sample_stocks[0].pk)
        self.assertEqual(stocks[1].pk, self.sample_stocks[1].pk)

    @patch.object(BaseClient, 'get_instance')
    @patch.object(GetProductPricesFromProductStocks, 'create_batch_objects')
    @patch.object(GetProductPricesFromProductStocks, 'create_integration_actions')
    @patch.object(GetProductPricesFromProductStocks, 'update_batch_request')
    def test_normalize_response(
        self,
        mock_update_batch_request,
        mock_create_integration_actions,
        mock_create_batch_objects,
        mock_get_instance
    ):
        data = self.get_product_prices_from_product_stocks.normalize_response(
            self.sample_stocks,
            None
        )
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0].pk, self.sample_stocks[0].pk)
        self.assertEqual(data[1].pk, self.sample_stocks[1].pk)

    @patch.object(GetProductPricesFromProductStocks, 'create_batch_objects')
    def test_create_integration_actions(
        self,
        mock_create_batch_objects
    ):
        self.get_product_prices_from_product_stocks.create_integration_actions(
            self.sample_stocks,
            []
        )
        self.assertEqual(mock_create_batch_objects.call_count, 1)

    def test_get_product_price_with_empty_stock(self):
        stocks = self.get_product_prices_from_product_stocks.get_product_price(
            []
        )
        self.assertEqual(stocks, [])

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelExtraProductPriceEndpoint, 'list')
    @patch.object(GetProductPricesFromProductStocks, 'get_prices')
    def test_get_product_price(
        self,
        mock_get_prices,
        mock_list,
        mock_get_instance
    ):
        example_response = MagicMock()
        example_response.list.return_value = self.sample_stocks
        example_response.iterator = iter(self.sample_stocks)

        with patch.object(
            ChannelExtraProductPriceEndpoint,
            '__new__',
            return_value=example_response
        ):
            stocks = self.get_product_prices_from_product_stocks.get_product_price(
                self.sample_stocks
            )

        self.assertEqual(len(stocks), 2)
        self.assertEqual(stocks[0].pk, self.sample_stocks[0].pk)
        self.assertEqual(stocks[1].pk, self.sample_stocks[1].pk)
        self.assertEqual(
            stocks[0].failed_reason_type, 
            FailedReasonType.channel_app.value
        )
        self.assertEqual(
            stocks[1].failed_reason_type, 
            FailedReasonType.channel_app.value
        )

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelExtraProductPriceEndpoint, 'list')
    def test_get_prices(
        self,
        mock_list,
        mock_get_instance
    ):
        product_prices = [
            MagicMock(
                pk=1,
                product=5,
                price='645670668.11',
                price_list=1,
                currency_type='try',
                tax_rate='32.61',
                retail_price=None,
                extra_field={},
                discount_percentage='63.57',
                modified_date='2024-01-02T07:53:06.392780Z',
                created_date='2024-01-02T07:53:06.392771Z',
                price_type='default'
            )
        ]
        
        example_response = MagicMock()
        example_response.list.return_value = product_prices
        example_response.iterator = iter(product_prices)

        with patch.object(
            ChannelExtraProductPriceEndpoint,
            '__new__',
            return_value=example_response
        ):
            stocks = self.get_product_prices_from_product_stocks.get_prices(
                "1,2,3",
                ChannelExtraProductPriceEndpoint()
            )
        
        self.assertEqual(len(stocks), 1)
        self.assertEqual(stocks[0].pk, product_prices[0].pk)
        self.assertEqual(stocks[0].product, product_prices[0].product)
        self.assertEqual(stocks[0].price, product_prices[0].price)


class TestGetProductStocksFromProductPrices(BaseTestCaseMixin):
    """
    Test case for GetProductStocksFromProductPrices
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetProductStocksFromProductPrices
    """

    def setUp(self) -> None:
        self.stocks = [
            MagicMock(
                pk=3,
                product=1,
                stock=0,
                stock_list=4,
                unit_type='qty',
                extra_field={},
                sold_quantity_unreported=0,
                modified_date='2023-12-19T08:38:48.476005Z',
                created_date='2023-12-19T08:38:48.475992Z'
            ),
        ]
        self.prices = [
            MagicMock(
                pk=1,
                product=5,
                price='645670668.11',
                price_list=1,
                currency_type='try',
                tax_rate='32.61',
                retail_price=None,
                extra_field={},
                discount_percentage='63.57',
                modified_date='2024-01-02T07:53:06.392780Z',
                created_date='2024-01-02T07:53:06.392771Z',
                price_type='default',
                failed_reason_type=FailedReasonType.channel_app.value
            )
        ]
        self.get_product_stocks_from_product_prices = GetProductStocksFromProductPrices(
            integration=self.mock_integration
        )

    @patch.object(BaseClient, 'get_instance')
    @patch.object(GetProductStocksFromProductPrices, 'get_product_stock')
    def test_get_data(self, mock_get_instance, mock_get_product_stock):
        self.get_product_stocks_from_product_prices.objects = self.prices
        self.assertEqual(
            self.get_product_stocks_from_product_prices.get_data(),
            self.prices
        )

    @patch.object(
        BaseClient, 
        'get_instance'
    )
    @patch.object(
        GetProductStocksFromProductPrices, 
        'create_batch_objects'
    )
    @patch.object(
        GetProductStocksFromProductPrices, 
        'create_integration_actions'
    )
    @patch.object(
        GetProductStocksFromProductPrices, 
        'update_batch_request'
    )
    def test_normalize_response(
        self,
        mock_update_batch_request,
        mock_create_integration_actions,
        mock_create_batch_objects,
        mock_get_instance
    ):
        data = self.get_product_stocks_from_product_prices.normalize_response(
            self.stocks,
            None
        )
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].pk, self.stocks[0].pk)

    @patch.object(GetProductStocksFromProductPrices, 'create_batch_objects')
    def test_create_integration_actions(self, mock_create_batch_objects):
        self.get_product_stocks_from_product_prices.create_integration_actions(
            self.stocks,
            []
        )
        self.assertEqual(mock_create_batch_objects.call_count, 1)

    def test_get_product_stock_with_empty_stock(self):
        self.stocks = []
        stocks = self.get_product_stocks_from_product_prices.get_product_stock(
            self.stocks
        )
        self.assertEqual(stocks, [])

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelExtraProductPriceEndpoint, 'list')
    @patch.object(GetProductStocksFromProductPrices, 'get_stocks')
    def test_get_product_stock(self, mock_get_stocks, mock_list, mock_get_instance):
        mock_get_stocks.return_value = self.stocks
        prices = self.get_product_stocks_from_product_prices.get_product_stock(
            self.prices
        )
        self.assertEqual(len(prices), 1)
        self.assertEqual(prices[0].pk, self.prices[0].pk)
        self.assertEqual(prices[0].product, self.prices[0].product)
        self.assertEqual(prices[0].price, self.prices[0].price)
        self.assertEqual(prices[0].failed_reason_type, FailedReasonType.channel_app.value)

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelExtraProductPriceEndpoint, 'list')
    def test_get_stocks(self, mock_list, mock_get_instance):
        example_response = MagicMock()
        example_response.list.return_value = self.stocks
        example_response.iterator = iter(self.stocks)

        with patch.object(
            ChannelExtraProductStockEndpoint,
            '__new__',
            return_value=example_response
        ):
            stocks = self.get_product_stocks_from_product_prices.get_stocks(
                "1,2,3",
                ChannelExtraProductStockEndpoint()
            )

        self.assertEqual(len(stocks), 1)
        self.assertEqual(stocks[0].pk, self.stocks[0].pk)
        self.assertEqual(stocks[0].product, self.stocks[0].product)
        self.assertEqual(stocks[0].stock, self.stocks[0].stock)


class TestGetInsertedProductStocksFromExtraStockList(BaseTestCaseMixin):
    """
    Test case for GetInsertedProductStocksFromExtraStockList
    run: python -m unittest channel_app.omnitron.commands.tests.test_products.TestGetInsertedProductStocksFromExtraStockList
    """

    def setUp(self) -> None:
        self.get_inserted_product_stocks_from_extra_stock_list = GetInsertedProductStocksFromExtraStockList(
            integration=self.mock_integration
        )
        self.sample_stocks = [
            ProductStock(
                pk=3,
                product=1,
                stock=0,
                stock_list=4,
                unit_type='qty',
                extra_field={},
                sold_quantity_unreported=0,
                remote_id=3,
                modified_date='2023-12-19T08:38:48.476005Z',
                created_date='2023-12-19T08:38:48.475992Z'
            ),
            ProductStock(
                pk=4,
                product=2,
                stock=0,
                stock_list=4,
                unit_type='qty',
                extra_field={},
                sold_quantity_unreported=0,
                remote_id=4,
                modified_date='2023-12-19T08:38:48.476005Z',
                created_date='2023-12-19T08:38:48.475992Z'
            )
        ]
        self.integration_actions = [
            MagicMock(
                pk=1,
                channel=2,
                content_type=ContentType.product_stock.value,
                object_id=self.sample_stocks[0].pk,
                remote_id=None,
                version_date="2023-12-28T10:28:17.186730Z",
                state={},
                modified_date="2023-12-28T10:28:17.187032Z",
                local_batch_id=None,
                status=None,
                created_date="2023-12-28T10:28:17.187014Z"
            ),
            MagicMock(
                pk=2,
                channel=2,
                content_type=ContentType.product_stock.value,
                object_id=self.sample_stocks[1].pk,
                remote_id=None,
                version_date="2023-12-28T10:28:17.186730Z",
                state={},
                modified_date="2023-12-28T10:28:17.187032Z",
                local_batch_id=None,
                status=None,
                created_date="2023-12-28T10:28:17.187014Z"
            )
        ]

    @patch.object(BaseClient, 'get_instance')
    @patch.object(ChannelIntegrationActionEndpoint, 'list')
    def test_get_integration_actions(self, mock_list, mock_get_instance):
        example_response = MagicMock()
        example_response.list.return_value = self.integration_actions
        example_response.iterator = iter(self.integration_actions)

        with patch.object(
            ChannelIntegrationActionEndpoint,
            '__new__',
            return_value=example_response
        ):
            stocks = self.get_inserted_product_stocks_from_extra_stock_list.get_integration_actions(
                self.sample_stocks
            )

        self.assertEqual(len(stocks), 2)
        self.assertEqual(stocks[0].pk, self.integration_actions[0].object_id)
        self.assertEqual(stocks[1].pk, self.integration_actions[1].object_id)
        self.assertEqual(stocks[0].remote_id, self.sample_stocks[0].remote_id)
        self.assertEqual(stocks[1].remote_id, self.sample_stocks[1].remote_id)
