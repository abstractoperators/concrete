import json
from dataclasses import dataclass


# TODO: Replace PydanticModel with dataclass
class ConcreteModel:
    pass


# # TODO: Remove this as a dependency
# class KombuMixin(PydanticModel):
#     """
#     Represents a Mixin to allow serialization and deserialization of subclasses
#     """

#     def __init_subclass__(cls, **kwargs):
#         register_type(
#             cls,
#             cls.__name__,
#             lambda model: model.model_dump_json(),
#             lambda model_json: cls.model_validate_json(model_json),
#         )
#         return super().__init_subclass__(**kwargs)
