from oaas_sdk2_py import Oparaca, BaseObject, ObjectInvocationRequest

oaas = Oparaca()

test = oaas.new_cls("test")
@test
class SampleObj(BaseObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = self.create_data_ref("d1")

    @test.func("fn-1")
    def sample_fn(self, req: ObjectInvocationRequest):
        print(req.payload)

    @test.func()
    def sample_fn2(self, req: ObjectInvocationRequest):
        print(req.payload)

    @test.func()
    def sample_fn3(self, req: ObjectInvocationRequest):
        print(req.payload)
