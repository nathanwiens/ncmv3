# Cradlepoint NCMv3 Python Module
This is a Python client library for Cradlepoint NCM APIv3

INSTALL AND RUN INSTRUCTIONS

1. Install the ncmv3 pip package, or copy the ncmv3.py file into your working directory:
    ```
    pip3 install ncmv3
    ```

2. Set your NCM APIv3 Key (without the "Bearer" prefix).
    ```
    api_key = "babwY0bNYqMwa0Kt0VTRknk6pqmOzNuz"
    ```

3. Import the module and create an instance of the NcmClient object:
   
   If using pip:
    ```
    from ncmv3 import ncmv3
    n3 = ncmv3.NcmClient(api_key=api_key)
    ```
   
   If not using pip:
    ```
    import ncmv3
    n3 = ncm.NcmClient(api_key=api_key)
    ```

4. Call functions from the module as needed. For example:
    ```
    print(n3.get_users())
    ```
   
USAGE AND TIPS:

This python class includes a few optimizations to make it easier to work with the API.
Cradlepoint's max page size is 50. This module allows specifying a higher limit than 50, which will handle page parsing automatically.

This can be modified by specifying a "limit parameter":
   ```
   n3.get_accounts(limit=10)
   ```
You can also return the full list of records in a single array without the need for paging
by passing limit=0:
   ```
   n3.get_accounts(limit=0)
   ```
