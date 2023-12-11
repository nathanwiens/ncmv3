"""
Cradlepoint NCM API class
Created by: Nathan Wiens

Overview:
    The purpose of this class is to make it easier for users to interact with
    the Cradlepoint NCM API. Within this class is a set of functions that
    closely matches the available API calls. Full documentation of the
    Cradlepoint NCM API is available at https://developer.cradlepoint.com.

Requirements:
    A Cradlepoint NCM APIv3 Key is required to make API calls.
    While the class can be instantiated without supplying an API key,
    any subsequent calls will fail unless the key is set via the
    set_api_key() method.

Usage:
    Instantiating the class:
        import ncmv3
        api_key = "babwY0bNYqMwa0Kt0VTRknk6pqmOzNuz"
        n3 = ncmv3.NcmClient(api_key=api_key)

    Example API call:
        n3.get_users()

Tips:
    This python class includes a few optimizations to make it easier to
    work with the API. The default record limit is set at 500 instead of
    the Cradlepoint default of 20, which reduces the number of API calls
    required to return large sets of data.

    This can be modified by specifying a "limit parameter":
       n3.get_users(limit=10)

    You can also return the full list of records in a single array without
    the need for paging by passing limit=0:
       n3.get_users(limit=0)

"""

from requests import Session
from requests.adapters import HTTPAdapter
from http import HTTPStatus
from urllib3.util.retry import Retry
import os
import json


def __is_json(test_json):
    """
    Checks if a string is a valid json object
    """
    try:
        json.loads(test_json)
    except ValueError:
        return False
    return True


class NcmClient:
    """
    This NCM Client class provides functions for interacting with =
    the Cradlepoint NCM API. Full documentation of the Cradlepoint API can be
    found at: https://developer.cradlepoint.com
    """

    def __init__(self,
                 api_key=None,
                 log_events=False,
                 retries=5,
                 retry_backoff_factor=2,
                 retry_on=None,
                 base_url=os.environ.get(
                     'CP_BASE_URL', 'https://api.cradlepointecm.com/api/v3')
                 ):
        """
        Constructor. Sets up and opens request session.
        :param api_key: API Bearer token (without the "Bearer" text).
          Optional, but must be set before calling functions.
        :type api_key: str
        :param log_events: if True, HTTP status info will be printed. False by default
        :type log_events: bool
        :param retries: number of retries on failure. Optional.
        :param retry_backoff_factor: backoff time multiplier for retries.
          Optional.
        :param retry_on: types of errors on which automatic retry will occur.
          Optional.
        :param base_url: # base url for calls. Configurable for testing.
          Optional.
        """
        if retry_on is None:
            retry_on = [
                HTTPStatus.REQUEST_TIMEOUT,
                HTTPStatus.GATEWAY_TIMEOUT,
                HTTPStatus.SERVICE_UNAVAILABLE
            ]
        self.log_events = log_events
        self.base_url = base_url
        self.session = Session()
        self.adapter = HTTPAdapter(
            max_retries=Retry(total=retries,
                              backoff_factor=retry_backoff_factor,
                              status_forcelist=retry_on,
                              redirect=3
                              )
        )
        self.session.mount(self.base_url, self.adapter)
        if api_key:
            token = {'Authorization': f'Bearer {api_key}'}
            self.session.headers.update(token)
        self.session.headers.update({
            'Content-Type': 'application/vnd.api+json',
            'Accept': 'application/vnd.api+json'
        })

    def __return_handler(self, status_code, returntext, obj_type):
        """
        Prints returned HTTP request information if self.logEvents is True.
        """
        if str(status_code) == '200':
            return f'{obj_type} operation successful.'
        elif str(status_code) == '201':
            if self.log_events:
                print('{0} created Successfully\n'.format(str(obj_type)))
            return returntext
        elif str(status_code) == '202':
            if self.log_events:
                print('{0} accepted Successfully\n'.format(str(obj_type)))
            return returntext
        elif str(status_code) == '204':
            if self.log_events:
                print('{0} deleted Successfully\n'.format(str(obj_type)))
            return returntext
        elif str(status_code) == '400':
            if self.log_events:
                print('Bad Request\n')
            return f'ERROR: {status_code}: {returntext}'
        elif str(status_code) == '401':
            if self.log_events:
                print('Unauthorized Access\n')
            return f'ERROR: {status_code}: {returntext}'
        elif str(status_code) == '404':
            if self.log_events:
                print('Resource Not Found\n')
            return f'ERROR: {status_code}: {returntext}'
        elif str(status_code) == '500':
            if self.log_events:
                print('HTTP 500 - Server Error\n')
            return f'ERROR: {status_code}: {returntext}'
        else:
            print(f'HTTP Status Code: {status_code} - {returntext}\n')

    def __get_json(self, get_url, call_type, params=None):
        """
        Returns full paginated results
        """
        results = []

        if params is not None and "limit" in params:
            limit = params['limit']
            if limit == 0:
                limit = 1000000
            if params['limit'] > 50 or params['limit'] == 0:
                params['page[size]'] = 50
            else:
                params['page[size]'] = params['limit']
        else:
            limit = 50

        url = get_url

        while url and (len(results) < limit):
            ncm = self.session.get(url, params=params)
            if not (200 <= ncm.status_code < 300):
                return self.__return_handler(ncm.status_code, ncm.json(), call_type)
            data = ncm.json()['data']
            if isinstance(data, list):
                self.__return_handler(ncm.status_code, data, call_type)
                for d in data:
                    results.append(d)
            else:
                results.append(data)
            if "links" in ncm.json():
                url = ncm.json()['links']['next']
            else:
                url = None

        if params is not None and "filter[fields]" in params.keys():
            data = []
            fields = params['filter[fields]'].split(",")
            for result in results:
                items = {}
                for k, v in result['attributes'].items():
                    if k in fields:
                        items[k] = v
                data.append(items)
            return data

        return results


    def __parse_kwargs(self, kwargs, allowed_params):
        """
        Checks for invalid parameters and missing API Keys, and handles "filter" fields
        """

        bad_params = {k: v for (k, v) in kwargs.items() if
                      k not in allowed_params if ("search" not in k and "filter" not in k and "sort" not in k)}
        if len(bad_params) > 0:
            raise ValueError("Invalid parameters: {}".format(bad_params))

        if 'Authorization' not in self.session.headers:
            raise KeyError(
                "API key missing. "
                "Please set API key before making API calls.")

        params = {}

        for key, val in kwargs.items():
            if "search" in key or "filter" in key or "sort" in key or "limit" in key:
                params[key] = val

            elif "__" in key:
                split_key = key.split("__")
                params[f'filter[{split_key[0]}][{split_key[1]}]'] = val
            else:
                params[f'filter[{key}]'] = val

        return params

    def __parse_search_kwargs(self, kwargs, allowed_params):
        """
        Checks for invalid parameters and missing API Keys, and handles "search" fields
        """

        bad_params = {k: v for (k, v) in kwargs.items() if
                      k not in allowed_params if ("search" not in k and "filter" not in k and "sort" not in k)}
        if len(bad_params) > 0:
            raise ValueError("Invalid parameters: {}".format(bad_params))

        if 'Authorization' not in self.session.headers:
            raise KeyError(
                "API key missing. "
                "Please set API key before making API calls.")

        params = {}

        for key, val in kwargs.items():
            if "filter" in key or "sort" in key or "limit" in key:
                params[key] = val
            elif "fields" in key:
                params[f'filter[{key}]'] = val
            else:
                if "search" not in key:
                    params[f'search[{key}]'] = val

        return params

    def __parse_put_kwargs(self, kwargs, allowed_params):
        """
        Checks for invalid parameters and missing API Keys, and handles "filter" fields
        """

        bad_params = {k: v for (k, v) in kwargs.items() if
                      k not in allowed_params if ("search" not in k and "filter" not in k and "sort" not in k)}
        if len(bad_params) > 0:
            raise ValueError("Invalid parameters: {}".format(bad_params))

        if 'Authorization' not in self.session.headers:
            raise KeyError(
                "API key missing. "
                "Please set API key before making API calls.")

        return kwargs

    def set_api_key(self, api_key):
        """
        Sets NCM API Keys for session.
        :param api_key: API Bearer token (without the "Bearer" prefix).
        :type api_key: str
        """
        if api_key:
            token = {'Authorization': f'Bearer {api_key}'}
            self.session.headers.update(token)
        return

    def get_users(self, **kwargs):
        """
        Returns users with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of users with details.
        """
        call_type = 'Users'
        get_url = f'{self.base_url}/beta/users'

        allowed_params = ['email',
                          'email__not',
                          'first_name',
                          'first_name__ne',
                          'id',
                          'is_active__ne',
                          'last_login',
                          'last_login__lt',
                          'last_login__lte',
                          'last_login__gt',
                          'last_login__gte',
                          'last_login__ne',
                          'last_name',
                          'last_name__ne',
                          'pending_email',
                          'fields',
                          'limit',
                          'sort']

        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def create_user(self, email, first_name, last_name, **kwargs):
        """
        Creates a user.
        :param email: Email address
        :type email: str
        :param first_name: First name
        :type first_name: str
        :param last_name: Last name
        :type last_name: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: User creation result.
        """
        call_type = 'User'
        post_url = f'{self.base_url}/beta/users'

        allowed_params = ['is_active',
                          'last_login',
                          'pending_email']
        params = self.__parse_kwargs(kwargs, allowed_params)
        params['email'] = email
        params['first_name'] = first_name
        params['last_name'] = last_name

        """GET TENANT ID"""
        t = self.get_subscriptions(limit=1)

        data = {
            "data": {
                "type": "users",
                "attributes": params,
                "relationships": {
                    "tenant": {
                        "data": [t[0]['relationships']['tenants']['data']]
                    }
                }
            }
        }

        ncm = self.session.post(post_url, data=json.dumps(data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def update_user(self, email, **kwargs):
        """
        Updates a user's date.
        :param email: Email address
        :type email: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: User update result.
        """
        call_type = 'Users'

        user = self.get_users(email=email)[0]
        user.pop('links')

        put_url = f'{self.base_url}/beta/users/{user["id"]}'

        allowed_params = ['first_name',
                          'last_name',
                          'is_active',
                          'user_id',
                          'last_login',
                          'pending_email']
        params = self.__parse_kwargs(kwargs, allowed_params)

        for k, v in params.items():
            user['attributes'][k] = v

        user = {"data": user}

        ncm = self.session.put(put_url, data=json.dumps(user))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def delete_user(self, email, **kwargs):
        """
        Updates a user's date.
        :param email: Email address
        :type email: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: None unless error.
        """
        call_type = 'Users'

        user = self.get_users(email=email)[0]
        user.pop('links')

        delete_url = f'{self.base_url}/beta/users/{user["id"]}'

        ncm = self.session.delete(delete_url)
        result = self.__return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def get_routers(self, **kwargs):
        """
        Returns users with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of routers with details.
        """
        call_type = 'Routers'
        get_url = f'{self.base_url}/asset_endpoints'

        allowed_params = ['id',
                          'hardware_series',
                          'hardware_series_key',
                          'mac_address',
                          'serial_number',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def get_subscriptions(self, **kwargs):
        """
        Returns subscriptions with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of subscriptions with details.
        """
        call_type = 'Subscriptions'
        get_url = f'{self.base_url}/subscriptions'

        allowed_params = ['end_time',
                          'end_time__lt',
                          'end_time__lte',
                          'end_time__gt',
                          'end_time__gte',
                          'end_time__ne',
                          'id',
                          'name',
                          'quantity',
                          'start_time',
                          'start_time__lt',
                          'start_time__lte',
                          'start_time__gt',
                          'start_time__gte',
                          'start_time__ne',
                          'tenant',
                          'type',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def get_private_cellular_networks(self, **kwargs):
        """
        Returns information about your private cellular networks.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of PCNs with details.
        """
        call_type = 'Private Cellular Networks'
        get_url = f'{self.base_url}/beta/private_cellular_networks'

        allowed_params = ['core_ip',
                          'created_at',
                          'created_at__lt',
                          'created_at__lte',
                          'created_at__gt',
                          'created_at__gte',
                          'created_at__ne',
                          'ha_enabled',
                          'id',
                          'mobility_gateways',
                          'mobility_gateway_virtual_ip',
                          'name',
                          'state',
                          'status',
                          'tac',
                          'type',
                          'updated_at',
                          'updated_at__lt',
                          'updated_at__lte',
                          'updated_at__gt',
                          'updated_at__gte',
                          'updated_at__ne',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def get_private_cellular_network(self, network_id, **kwargs):
        """
        Returns information about a private cellular network.
        :param network_id: ID of the private_cellular_networks record
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: An individual PCN network with details.
        """
        call_type = 'Private Cellular Networks'
        get_url = f'{self.base_url}/beta/private_cellular_networks/{network_id}'

        allowed_params = ['name',
                          'segw_ip',
                          'ha_enabled',
                          'mobility_gateway_virtual_ip',
                          'state',
                          'status',
                          'tac',
                          'created_at',
                          'updated_at',
                          'fields']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def update_private_cellular_network(self, id=None, name=None, **kwargs):
        """
        Make changes to a private cellular network.
        :param id: PCN network ID. Specify either this or name.
        :type id: str
        :param name: PCN network name
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: PCN update result.
        """
        call_type = 'Private Cellular Network'

        if not id and not name:
            return "ERROR: no network specified. Must specify either network_id or network_name"

        if id:
            net = self.get_private_cellular_networks(id=id)[0]
        elif name:
            net = self.get_private_cellular_networks(name=name)[0]

        if name:
            kwargs['name'] = name

        net.pop('links')

        put_url = f'{self.base_url}/beta/private_cellular_networks/{net["id"]}'

        allowed_params = ['core_ip',
                          'ha_enabled',
                          'id',
                          'mobility_gateways',
                          'mobility_gateway_virtual_ip',
                          'name',
                          'state',
                          'status',
                          'tac',
                          'type']
        params = self.__parse_put_kwargs(kwargs, allowed_params)

        for k, v in params.items():
            net['attributes'][k] = v

        data = {"data": net}

        ncm = self.session.put(put_url, data=json.dumps(data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def create_private_cellular_network(self, name, core_ip, ha_enabled=False, mobility_gateway_virtual_ip=None, mobility_gateways=None):
        """
        Make changes to a private cellular network.
        :param name: Name of the networks.
        :type name: str
        :param core_ip: IP address to reach core network.
        :type core_ip: str
        :param ha_enabled: High availability (HA) of network.
        :type ha_enabled: bool
        :param mobility_gateway_virtual_ip: Virtual IP address to reach core when HA is enabled. Nullable.
        :type mobility_gateway_virtual_ip: str
        :param mobility_gateways: Comma separated list of private_cellular_cores IDs to add as mobility gateways. Nullable.
        :type mobility_gateways: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Create PCN result..
        """
        call_type = 'Private Cellular Network'

        post_url = f'{self.base_url}/beta/private_cellular_networks'

        data = {
            "data": {
                "type": "private_cellular_networks",
                "attributes": {
                    "name": name,
                    "core_ip": core_ip,
                    "ha_enabled": ha_enabled,
                    "mobility_gateway_virtual_ip": mobility_gateway_virtual_ip
                }
            }
        }

        if mobility_gateways:
            relationships = {
                "mobility_gateways": {
                    "data": []
                }
            }
            gateways = mobility_gateways.split(",")

            for gateway in gateways:
                relationships['mobility_gateways']['data'].append({"type": "private_cellular_cores", "id": gateway})

            data['data']['relationships'] = relationships

        ncm = self.session.post(post_url, data=json.dumps(data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def delete_private_cellular_network(self, id):
        """
        Returns information about a private cellular network.
        :param id: ID of the private_cellular_networks record
        :type id: str
        :return: None unless error.
        """
        # TODO support deletion by network name
        call_type = 'Private Cellular Network'
        delete_url = f'{self.base_url}/beta/private_cellular_networks/{id}'

        ncm = self.session.delete(delete_url)
        result = self.__return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def get_private_cellular_cores(self, **kwargs):
        """
        Returns information about a private cellular core.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of Mobility Gateways with details.
        """
        call_type = 'Private Cellular Cores'
        get_url = f'{self.base_url}/beta/private_cellular_cores'

        allowed_params = ['created_at',
                          'id',
                          'management_ip',
                          'network',
                          'router',
                          'status',
                          'type',
                          'updated_at',
                          'url',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def get_private_cellular_core(self, core_id, **kwargs):
        """
        Returns information about a private cellular core.
        :param core_id: ID of the private_cellular_cores record
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: An individual Mobility Gateway with details.
        """
        call_type = 'Private Cellular Core'
        get_url = f'{self.base_url}/beta/private_cellular_cores/{core_id}'

        allowed_params = ['created_at',
                          'id',
                          'management_ip',
                          'network',
                          'router',
                          'status',
                          'type',
                          'updated_at',
                          'url',
                          'fields',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def get_private_cellular_radios(self, **kwargs):
        """
        Returns information about a private cellular radio.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of Cellular APs with details.
        """
        call_type = 'Private Cellular Radios'
        get_url = f'{self.base_url}/beta/private_cellular_radios'

        allowed_params = ['admin_state',
                          'antenna_azimuth',
                          'antenna_beamwidth',
                          'antenna_downtilt',
                          'antenna_gain',
                          'bandwidth',
                          'category',
                          'cpi_id',
                          'cpi_name',
                          'cpi_signature',
                          'created_at',
                          'description',
                          'fccid',
                          'height',
                          'height_type',
                          'id',
                          'indoor_deployment',
                          'latitude',
                          'location',
                          'longitude',
                          'mac',
                          'name',
                          'network',
                          'serial_number',
                          'tdd_mode',
                          'tx_power',
                          'type',
                          'updated_at',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def get_private_cellular_radio(self, id, **kwargs):
        """
        Returns information about a private cellular radio.
        :param id: ID of the private_cellular_radios record
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: An individual Cellular AP with details.
        """
        call_type = 'Private Cellular Radios'
        get_url = f'{self.base_url}/beta/private_cellular_radios/{id}'

        allowed_params = ['admin_state',
                          'antenna_azimuth',
                          'antenna_beamwidth',
                          'antenna_downtilt',
                          'antenna_gain',
                          'bandwidth',
                          'category',
                          'cpi_id',
                          'cpi_name',
                          'cpi_signature',
                          'created_at',
                          'description',
                          'fccid',
                          'height',
                          'height_type',
                          'id',
                          'indoor_deployment',
                          'latitude',
                          'location',
                          'longitude',
                          'mac',
                          'name',
                          'network',
                          'serial_number',
                          'tdd_mode',
                          'tx_power',
                          'type',
                          'updated_at',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def update_private_cellular_radio(self, id=None, name=None, **kwargs):
        """
        Updates a Cellular AP's data.
        :param id: ID of the private_cellular_radio record. Must specify this or name.
        :type id: str
        :param name: Name of the Cellular AP. Must specify this or id.
        type id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Update Cellular AP results.
        """
        call_type = 'Private Cellular Radio'

        if id:
            radio = self.get_private_cellular_radios(id=id)[0]
        elif name:
            radio = self.get_private_cellular_radios(name=name)[0]
        else:
            return "ERROR: Must specify either ID or name"

        if name:
            kwargs['name'] = name

        put_url = f'{self.base_url}/beta/private_cellular_radios/{radio["id"]}'

        if "network" in kwargs.keys():
            relationships = {
                "network": {
                    "data": {
                        "type": "private_cellular_networks",
                        "id": kwargs['network']
                    }
                }
            }
            kwargs.pop("network")

            radio['data']['relationships'] = relationships

        if "location" in kwargs.keys():
            location = {
                "data": {
                    "type": "private_cellular_radio_groups",
                    "id": kwargs['location']
                }
            }
            kwargs.pop("location")
            radio['data']['location'] = location

        allowed_params = ['admin_state',
                          'antenna_azimuth',
                          'antenna_beamwidth',
                          'antenna_downtilt',
                          'antenna_gain',
                          'bandwidth',
                          'category',
                          'cpi_id',
                          'cpi_name',
                          'cpi_signature',
                          'created_at',
                          'description',
                          'fccid',
                          'height',
                          'height_type',
                          'id',
                          'indoor_deployment',
                          'latitude',
                          'location',
                          'longitude',
                          'mac',
                          'name',
                          'network',
                          'serial_number',
                          'tdd_mode',
                          'tx_power']
        params = self.__parse_put_kwargs(kwargs, allowed_params)

        for k, v in params.items():
            radio['attributes'][k] = v

        radio = {"data": radio}

        ncm = self.session.put(put_url, data=json.dumps(radio))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def get_private_cellular_radio_groups(self, **kwargs):
        """
        Returns information about a private cellular core.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of Cellular AP Groups with details.
        """
        call_type = 'Private Cellular Radio Groups'
        get_url = f'{self.base_url}/beta/private_cellular_radio_groups'

        allowed_params = ['created_at',
                          'created_at__lt',
                          'created_at__lte',
                          'created_at__gt',
                          'created_at__gte',
                          'created_at__ne',
                          'description',
                          'id',
                          'name',
                          'network',
                          'type',
                          'updated_at',
                          'updated_at__lt',
                          'updated_at__lte',
                          'updated_at__gt',
                          'updated_at__gte',
                          'updated_at__ne',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def get_private_cellular_radio_group(self, group_id, **kwargs):
        """
        Returns information about a private cellular core.
        :param group_id: ID of the private_cellular_radio_groups record
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: An individual Cellular AP Group with details.
        """
        call_type = 'Private Cellular Radio Group'
        get_url = f'{self.base_url}/beta/private_cellular_radio_groups/{group_id}'

        allowed_params = ['created_at',
                          'description',
                          'id',
                          'name',
                          'network',
                          'type',
                          'updated_at',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def update_private_cellular_radio_group(self, id=None, name=None, **kwargs):
        """
        Updates a Radio Group.
        :param id: ID of the private_cellular_radio_groups record. Must specify this or name.
        :type id: str
        :param name: Name of the Radio Group. Must specify this or id.
        type name: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Update Cellular AP Group results.
        """
        call_type = 'Private Cellular Radio Group'

        if id:
            group = self.get_private_cellular_radio_groups(id=id)[0]
        elif name:
            group = self.get_private_cellular_radio_groups(name=name)[0]
        else:
            return "ERROR: Must specify either ID or name"

        if name:
            kwargs['name'] = name

        put_url = f'{self.base_url}/beta/private_cellular_sims/{group["id"]}'

        if "network" in kwargs.keys():
            relationships = {
                "network": {
                    "data": {
                        "type": "private_cellular_networks",
                        "id": kwargs['network']
                    }
                }
            }
            kwargs.pop("network")

            group['data']['relationships'] = relationships

        allowed_params = ['name',
                          'description']
        params = self.__parse_put_kwargs(kwargs, allowed_params)

        for k, v in params.items():
            group['attributes'][k] = v

        group = {"data": group}

        ncm = self.session.put(put_url, data=json.dumps(group))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def create_private_cellular_radio_group(self, name, description, network=None):
        """
        Creates a Radio Group.
        :param name: Name of the Radio Group.
        type name: str
        :param description: Description of the Radio Group.
        :type description: str
        param network: ID of the private_cellular_network to belong to. Optional.
        :type network: str
        :return: Create Private Cellular Radio Group results.
        """
        call_type = 'Private Cellular Radio Group'

        post_url = f'{self.base_url}/beta/private_cellular_radio_groups'

        group = {
            "data": {
                "type": "private_cellular_radio_groups",
                "attributes": {
                    "name": name,
                    "description": description
                }
            }
        }

        if network:
            relationships = {
                "network": {
                    "data": {
                        "type": "private_cellular_networks",
                        "id": network
                    }
                }
            }

            group['data']['relationships'] = relationships

        ncm = self.session.post(post_url, data=json.dumps(group))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def delete_private_cellular_radio_group(self, id):
        """
        Deletes a private_cellular_radio_group record.
        :param id: ID of the private_cellular_radio_group record
        :type id: str
        :return: None unless error.
        """
        #TODO support deletion by group name
        call_type = 'Private Cellular Radio Group'
        delete_url = f'{self.base_url}/beta/private_cellular_radio_group/{id}'

        ncm = self.session.delete(delete_url)
        result = self.__return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def get_private_cellular_sims(self, **kwargs):
        """
        Returns information about a private cellular core.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of PCN SIMs with details.
        """
        call_type = 'Private Cellular SIMs'
        get_url = f'{self.base_url}/beta/private_cellular_sims'

        allowed_params = ['created_at',
                          'created_at__lt',
                          'created_at__lte',
                          'created_at__gt',
                          'created_at__gte',
                          'created_at__ne',
                          'iccid',
                          'id',
                          'imsi',
                          'last_contact_at',
                          'last_contact_at__lt',
                          'last_contact_at__lte',
                          'last_contact_at__gt',
                          'last_contact_at__gte',
                          'last_contact_at__ne',
                          'name',
                          'network',
                          'state',
                          'state_updated_at',
                          'state_updated_at__lt',
                          'state_updated_at__lte',
                          'state_updated_at__gt',
                          'state_updated_at__gte',
                          'state_updated_at__ne',
                          'type',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def get_private_cellular_sim(self, id, **kwargs):
        """
        Returns information about a private cellular core.
        :param sim_id: ID of the private_cellular_sims record
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: An individual PCN SIM with details.
        """
        call_type = 'Private Cellular SIMs'
        get_url = f'{self.base_url}/beta/private_cellular_sims/{id}'

        allowed_params = ['created_at',
                          'iccid',
                          'id',
                          'imsi',
                          'last_contact_at',
                          'name',
                          'network',
                          'state',
                          'state_updated_at',
                          'type',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def update_private_cellular_sim(self, id=None, iccid=None, imsi=None, **kwargs):
        """
        Updates a SIM's data.
        :param id: ID of the private_cellular_sim record. Must specify ID, ICCID, or IMSI.
        :type id: str
        :param iccid: ICCID. Must specify ID, ICCID, or IMSI.
        :type id: str
        :param imsi: IMSI. Must specify ID, ICCID, or IMSI.
        :type id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Update PCN SIM results.
        """
        call_type = 'Private Cellular SIM'

        if id:
            sim = self.get_private_cellular_sims(id=id)[0]
        elif iccid:
            sim = self.get_private_cellular_sims(iccid=iccid)[0]
        elif imsi:
            sim = self.get_private_cellular_sims(imsi=imsi)[0]
        else:
            return "ERROR: Must specify either ID, ICCID, or IMSI"

        put_url = f'{self.base_url}/beta/private_cellular_sims/{sim["id"]}'

        if "network" in kwargs.keys():
            relationships = {
                "network": {
                    "data": {
                        "type": "private_cellular_networks",
                        "id": kwargs['network']
                    }
                }
            }
            kwargs.pop("network")

            sim['data']['relationships'] = relationships

        allowed_params = ['name',
                          'state']
        params = self.__parse_put_kwargs(kwargs, allowed_params)

        for k, v in params.items():
            sim['attributes'][k] = v

        sim = {"data": sim}

        ncm = self.session.put(put_url, data=json.dumps(sim))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def get_private_cellular_radio_statuses(self, **kwargs):
        """
        Returns information about a private cellular core.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Cellular radio status for all cellular radios.
        """
        call_type = 'Private Cellular Radio Statuses'
        get_url = f'{self.base_url}/beta/private_cellular_radio_statuses'

        allowed_params = ['admin_state',
                          'boot_time',
                          'cbrs_sas_status',
                          'cell',
                          'connected_ues',
                          'ethernet_status',
                          'id',
                          'ipsec_status',
                          'ipv4_address',
                          'last_update_time',
                          'online_status',
                          'operational_status',
                          'operating_tx_power',
                          's1_status',
                          'time_synchronization',
                          'type',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def get_private_cellular_radio_status(self, status_id, **kwargs):
        """
        Returns information about a private cellular core.
        :param status_id: ID of the private_cellular_radio_statuses resource
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Cellular radio status for an individual radio.
        """
        call_type = 'Private Cellular Radio Status'
        get_url = f'{self.base_url}/beta/private_cellular_radio_statuses/{status_id}'

        allowed_params = ['admin_state',
                          'boot_time',
                          'cbrs_sas_status',
                          'cell',
                          'connected_ues',
                          'ethernet_status',
                          'id',
                          'ipsec_status',
                          'ipv4_address',
                          'last_update_time',
                          'online_status',
                          'operational_status',
                          'operating_tx_power',
                          's1_status',
                          'time_synchronization',
                          'type',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results


    def get_public_sim_mgmt_assets(self, **kwargs):
        """
        Returns information about SIM asset resources in your NetCloud Manager account.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: SIM asset resources.
        """
        call_type = 'Private Cellular Radio Status'
        get_url = f'{self.base_url}/beta/public_sim_mgmt_assets'

        allowed_params = ['assigned_imei',
                          'carrier',
                          'detected_imei',
                          'device_status',
                          'iccid',
                          'is_licensed'
                          'type',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results

    def get_public_sim_mgmt_rate_plans(self, **kwargs):
        """
        Returns information about rate plan resources associated with the SIM assets in your NetCloud Manager account.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Rate plans for SIM assets.
        """
        call_type = 'Private Cellular Radio Status'
        get_url = f'{self.base_url}/beta/public_sim_mgmt_assets'

        allowed_params = ['carrier',
                          'name',
                          'status',
                          'fields',
                          'limit',
                          'sort']
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        results = self.__get_json(get_url, call_type, params=params)
        return results


    def get_exchange_sites(self, **kwargs):
        """
        Returns exchange sites.
        :param kwargs: A set of zero or more allowed parameters
        in the allowed_params list.
        :return: A list of exchange sites or a single site if site_id is provided.
        """
        call_type = 'Exchange Sites'
        get_url = f'{self.base_url}/beta/exchange_sites'

        if 'site_id' in kwargs:
            get_url += f'/{kwargs["site_id"]}'
            response = self.__get_json(get_url, call_type)
            return response

        allowed_params = ['exchange_network',
                        'name',
                        'fields',
                        'limit',
                        'sort']

        params = None
        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)

        response = self.__get_json(get_url, call_type, params=params)
        return response

    def create_exchange_site(self, name, exchange_network_id, router_id, local_domain=None, primary_dns=None, secondary_dns=None, lan_as_dns=False):
        """
        Creates an exchange site.
        :param name: Name of the exchange site.
        :type name: str
        :param primary_dns: Primary DNS of the exchange site.
        :type primary_dns: str
        :param secondary_dns: Secondary DNS of the exchange site.
        :type secondary_dns: str
        :param lan_as_dns: Whether LAN is used as DNS.
        :type lan_as_dns: bool
        :param local_domain: Local domain of the exchange site.
        :type local_domain: str
        :param exchange_network_id: ID of the exchange network.
        :type exchange_network_id: str
        :param router_id: ID of the endpoint.
        :type router_id: str
        :return: The response from the POST request.
        """
        call_type = 'Create Exchange Site'

        post_url = f'{self.base_url}/beta/exchange_sites'

        data = {
            "data": {
                "type": "exchange_user_managed_sites",
                "attributes": {
                    "name": name,
                    "primary_dns": primary_dns,
                    "secondary_dns": secondary_dns,
                    "lan_as_dns": lan_as_dns,
                    "local_domain": local_domain
                },
                "relationships": {
                    "exchange_network": {
                        "data": {
                            "id": exchange_network_id,
                            "type": "exchange_networks"
                        }
                    },
                    "endpoints": {
                        "data": [
                            {
                                "id": router_id,
                                "type": "endpoints"
                            }
                        ]
                    }
                }
            }
        }

        ncm = self.session.post(post_url, data=json.dumps(data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        if ncm.status_code == 201:
            return ncm.json()['data']
        else:
            return result

    def update_exchange_site(self, site_id, **kwargs):
        """
        Updates an exchange site.
        :param site_id: ID of the exchange site to update.
        :type site_id: str
        :param kwargs: Keyword arguments for the attributes and relationships of the exchange site.
        :return: The response from the PUT request.
        """
        call_type = 'Update Exchange Site'
        put_url = f'{self.base_url}/beta/exchange_sites/{site_id}'

        allowed_params = ['name', 'primary_dns', 'secondary_dns', 'lan_as_dns', 'local_domain']

        current_site = self.get_exchange_sites(site_id=site_id)[0]
        exchange_network_id = current_site['relationships']['exchange_network']['data']['id']
        router_id = current_site['relationships']['endpoints']['data'][0]['id']
        attributes = current_site['attributes']

        for key, value in kwargs.items():
            if key in allowed_params:
                attributes['key'] = value
        print(attributes)

        ncm = self.session.put(put_url, data=json.dumps({
            "data": {
                "type": "exchange_user_managed_sites",
                "id": site_id,
                "attributes": attributes,
                "relationships": {
                    "exchange_network": {
                        "data": {
                            "type": "exchange_networks",
                            "id": exchange_network_id
                        }
                    },
                    "endpoints": {
                        "data": [{
                            "type": "routers",
                            "id": router_id
                        }]
                    }
                }
            }
        }))

        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def delete_exchange_site(self, site_id):
        """
        Deletes an exchange site.
        :param site_id: ID of the exchange site to delete.
        :type site_id: str
        :return: The response from the DELETE request.
        """
        call_type = 'Delete Exchange Site'
        delete_url = f'{self.base_url}/beta/exchange_sites{site_id}'

        ncm = self.session.delete(delete_url)
        result = self.__return_handler(ncm.status_code, ncm, call_type)
        return result

    def get_exchange_resources(self, exchange_network=None, exchange_site=None, **kwargs):
        """
        Returns exchange sites.
        :param kwargs: A set of zero or more allowed parameters
        in the allowed_params list.
        :return: A list of exchange sites or a single site if site_id is provided.
        """
        call_type = 'Exchange Resources'
        get_url = f'{self.base_url}/beta/exchange_resources'

        params = {}

        allowed_params = ['exchange_network',
                          'name',
                          'id',
                          'fields',
                          'limit',
                          'sort']

        if kwargs:
            if "search" not in kwargs.keys():
                params = self.__parse_kwargs(kwargs, allowed_params)
            else:
                if kwargs['search']:
                    params = self.__parse_search_kwargs(kwargs, allowed_params)
                else:
                    params = self.__parse_kwargs(kwargs, allowed_params)

        if exchange_site:
            params['filter[exchange_site]'] = exchange_site
        elif exchange_network:
            params['filter[exchange_network]'] = exchange_network

        response = self.__get_json(get_url, call_type, params=params)
        return response

    def create_exchange_resource(self, site_id, resource_name, resource_type, **kwargs):
        """
        Creates an exchange site.
        :param site_id: NCX Site ID to add the resource to.
        :type site_id: str
        :param resource_name: Name for the new resource
        :type resource_type: str
        :param resource_type: exchange_fqdn_resources, exchange_wildcard_fqdn_resources, or exchange_ipsubnet_resources
        :type resource_type: str

        :return: The response from the POST request.
        """
        call_type = 'Create Exchange Site Resource'

        post_url = f'{self.base_url}/beta/exchange_resources'
        allowed_params = ['name',
                          'protocols',
                          'tags',
                          'domain',
                          'ip',
                          'static_prime_ip',
                          'port_ranges',
                          'fields',
                          'limit',
                          'sort']

        attributes = {key: value for key, value in kwargs.items() if key in allowed_params}
        attributes['name'] = resource_name

        data = {
            "data": {
                "type": resource_type,
                "attributes": attributes,
                "relationships": {
                    "exchange_site": {
                        "data": {
                            "id": site_id,
                            "type": "exchange_sites"
                        }
                    }
                }
            }
        }

        ncm = self.session.post(post_url, data=json.dumps(data))
        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        if ncm.status_code == 201:
            return ncm.json()['data']
        else:
            return result

    def update_exchange_resource(self, resource_id, exchange_network=None, exchange_site=None, **kwargs):
        """
        Updates an exchange site.
        :param resource_id: ID of the exchange resource to update.
        :type resource_id: str
        :param kwargs: Keyword arguments for the attributes and relationships of the exchange site.
        :return: The response from the PUT request.
        """
        call_type = 'Update Exchange Site'
        put_url = f'{self.base_url}/beta/exchange_resources/{resource_id}'

        allowed_params = ['name',
                          'protocols',
                          'tags',
                          'domain',
                          'ip',
                          'static_prime_ip',
                          'port_ranges']

        if exchange_site:
            current_resource = self.get_exchange_resources(exchange_site=exchange_site, id=resource_id)[0]
        elif exchange_network:
            current_resource = self.get_exchange_resources(exchange_network=exchange_network, id=resource_id)[0]

        exchange_site_id = current_resource['relationships']['exchange_site']['data']['id']
        attributes = current_resource['attributes']

        for key, value in kwargs.items():
            if key in allowed_params:
                attributes['key'] = value

        ncm = self.session.put(put_url, data=json.dumps({
            "data": {
                "type": current_resource['type'],
                "id": resource_id,
                "attributes": attributes,
                "relationships": {
                    "exchange_site": {
                        "data": {
                            "type": "exchange_sites",
                            "id": exchange_site_id
                        }
                    }
                }
            }
        }))

        result = self.__return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def delete_exchange_resource(self, resource_id):
        """
        Deletes an exchange resource.
        :param resource_id: ID of the exchange resource to delete.
        :type resource_id: str
        :return: The response from the DELETE request.
        """
        call_type = 'Delete Exchange Site'
        delete_url = f'{self.base_url}/beta/exchange_resources{resource_id}'

        ncm = self.session.delete(delete_url)
        result = self.__return_handler(ncm.status_code, ncm, call_type)
        return result

'''
    def get_group_modem_upgrade_jobs(self, **kwargs):
        """
        Returns users with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of users with details.
        """
        call_type = 'Group Modem Upgrades'
        get_url = f'{self.base_url}/beta/group_modem_upgrade_jobs'

        allowed_params = ['id',
                          'group_id',
                          'module_id',
                          'carrier_id',
                          'overwrite',
                          'active_only',
                          'upgrade_only',
                          'batch_size',
                          'created_at',
                          'created_at__lt',
                          'created_at__lte',
                          'created_at__gt',
                          'created_at__gte',
                          'created_at__ne',
                          'updated_at',
                          'updated_at__lt',
                          'updated_at__lte',
                          'updated_at__gt',
                          'updated_at__gte',
                          'updated_at__ne',
                          'available_version',
                          'modem_count',
                          'success_count',
                          'failed_count',
                          'statuscarrier_name',
                          'module_name',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_group_modem_upgrade_job(self, job_id, **kwargs):
        """
        Returns users with details.
        :param job_id: The ID of the job
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of users with details.
        """
        call_type = 'Group Modem Upgrades'
        get_url = f'{self.base_url}/beta/group_modem_upgrade_jobs/{job_id}'

        allowed_params = ['id',
                          'group_id',
                          'module_id',
                          'carrier_id',
                          'overwrite',
                          'active_only',
                          'upgrade_only',
                          'batch_size',
                          'created_at',
                          'updated_at',
                          'available_version',
                          'modem_count',
                          'success_count',
                          'failed_count',
                          'statuscarrier_name',
                          'module_name',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_group_modem_upgrade_summary(self, **kwargs):
        """
        Returns users with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of users with details.
        """
        call_type = 'Group Modem Upgrades'
        get_url = f'{self.base_url}/beta/group_modem_upgrade_jobs'

        allowed_params = ['group_id',
                          'module_id',
                          'module_name',
                          'upgradable_modems',
                          'up_to_date_modems',
                          'summary_data',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_group_modem_upgrade_device_summary(self, **kwargs):
        """
        Returns users with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of users with details.
        """
        call_type = 'Group Modem Upgrades'
        get_url = f'{self.base_url}/beta/group_modem_upgrade_jobs'

        allowed_params = ['group_id',
                          'module_id',
                          'carrier_id',
                          'overwrite',
                          'active_only',
                          'upgrade_only',
                          'router_name',
                          'net_device_name',
                          'current_version',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        if "search" not in kwargs.keys():
            params = self.__parse_kwargs(kwargs, allowed_params)
        else:
            if kwargs['search']:
                params = self.__parse_search_kwargs(kwargs, allowed_params)
            else:
                params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)
'''
