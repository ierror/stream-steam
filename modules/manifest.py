from abc import ABC, abstractmethod


class AbstractManifest(ABC):
    @property
    @abstractmethod
    def id(self):
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def description(self):
        pass

    @property
    @abstractmethod
    def install_warning(self):
        pass

    @classmethod
    @abstractmethod
    def print_howto(cls, *args, **kwargs):
        pass

    @abstractmethod
    def pre_deploy(self, *args, **kwargs):
        pass

    @abstractmethod
    def post_deploy(self, *args, **kwargs):
        pass

    @abstractmethod
    def pre_destroy(self, *args, **kwargs):
        pass

    @abstractmethod
    def post_destroy(self, *args, **kwargs):
        pass

    def build_resource_name(self, name=None):
        res_name = f"{self.root_stack.build_resource_name(self.id)}"
        if name:
            res_name = f"{res_name}-{name}"
        return res_name

    def __init__(self, root_stack):
        self.root_stack = root_stack
