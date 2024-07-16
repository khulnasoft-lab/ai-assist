class ServiceResponse:
    def __init__(self, success, result=None, error=None):
        self.success = success
        self.result = result
        self.error = error
