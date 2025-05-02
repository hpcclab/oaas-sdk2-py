import json
from oaas_sdk2_py.config import OprcConfig
from oaas_sdk2_py.engine import BaseObject, Oparaca

def object_detection(image_bytes: bytes):
    pass



IMAGE_KEY = 0
oaas = Oparaca(config=OprcConfig())
image_cls = oaas.new_cls(pkg="example", name="image")

@image_cls
class OaasImage(BaseObject):
    
    @image_cls.func()
    async def new(self, image: bytes):
        self.set_data(IMAGE_KEY, image)
        
    @image_cls.func()
    async def detect(self) -> str:
        image_bytes = await self.get_data(IMAGE_KEY)
        if image_bytes is None:
            raise ValueError("Image data not found")
        result = object_detection(image_bytes)  # Execute object detection
        summary = result.summary()
        return json.dumps({'label': summary})
    

async def example_usage():
    ctx = oaas.new_session()
    image = ctx.create_object(image_cls)
    with open("file.mp4", "rb") as file:
        await image.new(image=file.read())
    result = await image.detect()
    print(result)