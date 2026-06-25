from repositories.farmer_repository import FarmerRepository


class FarmerService:

    def __init__(self):
        self.repository = FarmerRepository()

    def create_farmer(self, farmer_data: dict):
        return self.repository.create(farmer_data)

    def get_farmer(self, farmer_id: str):
        return self.repository.get_by_id(farmer_id)

    def list_farmers(self):
        return self.repository.list_all()