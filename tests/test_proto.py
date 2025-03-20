from oaas_sdk2_py.pb.oprc import ObjData, ObjMeta, ValData


def test_proto():
    o1 = ObjData(
        metadata=ObjMeta(
            cls_id="example.hello",
            partition_id=1,
            object_id=1,),
        entries={
            1: ValData(byte=b"How are you?", crdt_map=b"te"),
        }
    )
    # b = b'\n\x11\n\rexample.hello\x18\x01\x12\x10\x12\x0e\n\x0cHow are you?'
    b = bytes(o1)
    # b = o1.SerializeToString()
    print(b)
    o = ObjData.FromString(b)
    print(o)