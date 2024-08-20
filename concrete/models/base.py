from kombu.utils.json import register_type
from pydantic import BaseModel


class ConcreteBaseModel(BaseModel):
    def __str__(self):
        return self.model_dump_json(indent=2)

    def __repr__(self):
        return self.__str__()


class KombuMixin(BaseModel):
    def __init_subclass__(cls, **kwargs):
        register_type(
            cls,
            cls.__name__,
            lambda model: model.model_dump_json(),
            lambda model_json: cls.model_validate_json(model_json),
        )
        return super().__init_subclass__(**kwargs)
