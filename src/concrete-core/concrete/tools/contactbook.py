from concrete.tools import MetaTool


class ContactMeta(MetaTool):
    """
    Modify self-declaration of contact book to include a description of contacts
    """

    def __str__(cls):
        super_str = MetaTool.__str__(ContactBook).replace("ContactBook", cls.__name__)
        contacts = "\nContacts:" + "\n".join(
            f"""
   - {name}
\t{val['description']}
"""
            for name, val in cls.contacts.items()
        )
        return super_str + contacts


class ContactBook(metaclass=ContactMeta):
    # Add universal contacts onto the class
    # To create a new contact book from scratch, modify contacts
    # on the instance of the tool
    contacts: dict[str, dict] = {}

    @property
    def contact_data(self) -> dict:
        return self.contacts

    @classmethod
    def message(cls, sender: str, receiver: str, body: str) -> str:
        """
        sender (str): The agent initiating contact
        receiver (str): The intended recipient
        body (str): The contents of the message
        """
        if receiver not in cls.contacts:
            raise ValueError("Contact not found")
        return f"{receiver} says 'Do not include a dark mode'"
