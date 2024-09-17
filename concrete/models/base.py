import json

from kombu.utils.json import register_type
from pydantic import BaseModel as PydanticModel


class ConcreteModel(PydanticModel):
    def __str__(self):
        # Remove tools from output if empty to improve prompt chaining quality.
        # Unfortunately, still affected by nesting of tools.
        model_dict = self.model_dump(mode="json", exclude_unset=True, exclude_none=True)
        if not model_dict.get("tools"):
            model_dict.pop("tools", None)

        # I give up on finding a better way to format this string.
        # f'{model_str} doesn't work
        # re.sub is more elegant, but its basically the same thing
        model_str = (
            json.dumps(model_dict, indent=4)
            .replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace("\\'", "'")
            .replace('\\"', '"')
        )

        return model_str

    def __repr__(self):
        model_dict = self.model_dump(mode="json", exclude_unset=True, exclude_none=True)
        return json.dumps(model_dict, indent=4)


class KombuMixin(PydanticModel):
    """
    Represents a Mixin to allow serialization and deserialization of subclasses
    """

    def __init_subclass__(cls, **kwargs):
        register_type(
            cls,
            cls.__name__,
            lambda model: model.model_dump_json(),
            lambda model_json: cls.model_validate_json(model_json),
        )
        return super().__init_subclass__(**kwargs)
