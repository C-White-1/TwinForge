# model/twin.py

from dataclasses import dataclass, field


@dataclass
class Twin:
    plant: Plant
    metadata: dict = field(default_factory=dict)
    
    def add_controller(self, controller: Controller):
        self.plant.controllers.append(controller)
        
    def controllers(self):
        return self.plant.controllers
        
    
