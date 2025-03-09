"""
Dependency Injection Container

Provides a lightweight dependency injection system for managing
service lifecycles and dependencies throughout the application.
"""

import inspect
from typing import Dict, Any, Type, TypeVar, Callable, Optional, Set, get_type_hints

T = TypeVar('T')

class DependencyError(Exception):
    """Exception raised for dependency injection errors"""
    pass

class ServiceRegistration:
    """Represents a registered service in the container"""
    
    def __init__(self, service_type: Type, factory: Callable[[], Any], singleton: bool = True):
        self.service_type = service_type
        self.factory = factory
        self.singleton = singleton
        self.instance = None
    
    def get_instance(self, container: 'Container') -> Any:
        """Get or create an instance of the service"""
        if self.singleton:
            if self.instance is None:
                self.instance = self.factory()
            return self.instance
        else:
            return self.factory()

class Container:
    """
    Dependency Injection Container
    
    Manages service registration, resolution, and lifecycle.
    Supports singleton and transient services.
    """
    
    def __init__(self):
        """Initialize the container"""
        self._registrations: Dict[Type, ServiceRegistration] = {}
        self._resolving: Set[Type] = set()
    
    def register(self, service_type: Type[T], implementation: Optional[Type] = None, 
                factory: Optional[Callable[[], T]] = None, singleton: bool = True) -> None:
        """
        Register a service with the container
        
        Args:
            service_type: The type to register (usually an interface or base class)
            implementation: The concrete implementation to use (optional)
            factory: A factory function that creates instances (optional)
            singleton: Whether to reuse a single instance (True) or create new ones (False)
        
        Notes:
            - Either implementation or factory must be provided, but not both
            - If implementation is provided, its constructor will be called automatically
              with dependencies resolved from the container
        """
        if implementation and factory:
            raise DependencyError("Cannot provide both implementation and factory")
        
        if implementation:
            # Create a factory that constructs the implementation with dependencies
            factory = lambda: self._create_instance(implementation)
        elif not factory:
            raise DependencyError("Must provide either implementation or factory")
        
        self._registrations[service_type] = ServiceRegistration(
            service_type=service_type,
            factory=factory,
            singleton=singleton
        )
    
    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service from the container
        
        Args:
            service_type: The type to resolve
            
        Returns:
            An instance of the requested service
            
        Raises:
            DependencyError: If the service is not registered or there is a circular dependency
        """
        if service_type not in self._registrations:
            raise DependencyError(f"Service {service_type.__name__} is not registered")
        
        if service_type in self._resolving:
            raise DependencyError(f"Circular dependency detected: {service_type.__name__}")
        
        self._resolving.add(service_type)
        try:
            return self._registrations[service_type].get_instance(self)
        finally:
            self._resolving.remove(service_type)
    
    def _create_instance(self, implementation_type: Type[T]) -> T:
        """
        Create an instance of a type, resolving constructor parameters from the container
        """
        # Get constructor signature
        init_signature = inspect.signature(implementation_type.__init__)
        init_params = init_signature.parameters
        
        # Skip self parameter
        params = list(init_params.values())[1:]
        
        # Get constructor parameter types using type hints
        type_hints = get_type_hints(implementation_type.__init__)
        
        # Build arguments for the constructor
        args = []
        for param in params:
            param_name = param.name
            
            # Skip **kwargs parameters
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                continue
                
            # Get the parameter type from type hints if available
            param_type = type_hints.get(param_name, Any)
            
            # Resolve the dependency if it has a type annotation
            if param_type is not Any:
                try:
                    arg = self.resolve(param_type)
                    args.append(arg)
                except DependencyError:
                    # If parameter has a default value, use it
                    if param.default is not inspect.Parameter.empty:
                        args.append(param.default)
                    else:
                        raise DependencyError(
                            f"Cannot resolve parameter '{param_name}' of type {param_type.__name__} "
                            f"for {implementation_type.__name__}"
                        )
            else:
                # If parameter has a default value, use it
                if param.default is not inspect.Parameter.empty:
                    args.append(param.default)
                else:
                    raise DependencyError(
                        f"Parameter '{param_name}' has no type annotation and no default value "
                        f"in {implementation_type.__name__}"
                    )
        
        # Create the instance
        return implementation_type(*args)
