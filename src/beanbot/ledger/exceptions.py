class Rejection(Exception):
    def __init__(self, reasons):
        self.reasons = reasons
