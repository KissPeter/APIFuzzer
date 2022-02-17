from json_ref_dict import materialize, RefDict

f1 = '/home/kissp/git/APIFuzzer/bug1_resolved.json'
f2 = '/home/kissp/git/APIFuzzer/resolved_mp.json'


# schema = materialize(RefDict("https://json-schema.org/draft-04/schema#/"))
def resolve(f):
    return materialize(RefDict(f))


schema1 = resolve(f1)
print(len(schema1))
schema2 = resolve(f2)
print(len(schema2))
assert schema1 == schema2, f's1:{schema1.keys()}\n s2:{schema2.keys()}'
