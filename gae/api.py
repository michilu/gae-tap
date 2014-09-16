import endpoints

import api_sample.v1

api_services = list()
api_services.extend(api_sample.v1.api_services)
app = endpoints.api_server(api_services)
