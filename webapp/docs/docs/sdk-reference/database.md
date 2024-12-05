# Database

Concrete's database integration requires the installation of package `concrete-db`

```bash
pip install concrete-db
```

We use SQLModel, which is a layer built on top of the popular SQLAlchemy ORM.

## ORM

Concrete provides several prebuilt ORM models. Included, but not limited to, `Operator`, `Orchestrator`, `Client`, `Tool`, `User`, `Message`. Most models also have a corresponding `ModelCreate` and `ModelUpdate` class, with `Create` models requiring fields, and `Update` models having optional fields. All models require a `ModelBase` class, which is their base class specifying the fields they have.

 ORM Models are representations of sdk objects in the database. As an example, the `Orchestrator` model represents a `concrete. orchestrators.Orchestrator` object.

Snippet of the `Orchestrator` model:

```python
class Orchestrator(OrchestratorBase, MetadataMixin, table=True):
    user: "User" = Relationship(back_populates="orchestrators")

    operators: list["Operator"] = Relationship(
        back_populates="orchestrator",
        cascade_delete=True,
    )
    projects: list["Project"] = Relationship(
        back_populates="orchestrator",
        cascade_delete=True,
    )
    tools: list["Tool"] = Relationship(back_populates="orchestrator", link_model=OrchestratorToolLink)class 

```

> Note the `OrchestratorBase` class, which is the base class for `Orchestrator`, specifying the fields it has. The `MetadataMixin` class is a mixin class adding metadata like `id`, `created_at`, `updated_at` to the model.

## Database Setup

By default, `concrete-db` configures and uses a local `sqlite` database. You can change this connection by setting your environment variables.

```.env
DB_DRIVER=postgresql+psycopg
DB_USERNAME=username
DB_PASSWORD=password
DB_PORT=5432
DB_HOST=localhost
DB_DATABASE=database
```

## Saving Automatically

Fortunately, you don't need to worry about implementation to save objects with the `concrete` sdk. All you need to do is specify `save_messages=True` when creating a `concrete.orchestrators.SoftwareOrchestrator` object. This will save messages passing through it to the database.

## Saving Manually

If you need to save objects manually, use a database `Session` object. The `Session` object is a context manager handling the database connection and transaction.

Example

```python
from concrete_db import Session
from concrete_db.orm.models import MetadataMixin, Base

class MyModel(Base, MetadataMixin):
    pass

with Session() as session:
    my_model = MyModel()
    session.add(my_model)
    session.commit()
```

---

Last Updated: 2024-12-04 09:21:32 UTC

Lines Changed: +5, -2
