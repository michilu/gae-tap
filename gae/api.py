import endpoints

import app_sample

api_services = list()
api_services.extend(app_sample.api_services)
app = endpoints.api_server(api_services)
