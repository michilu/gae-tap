import endpoints

import main_api_v1

api_services = list()
api_services.extend(main_api_v1.api_services)
app = endpoints.api_server(api_services)
