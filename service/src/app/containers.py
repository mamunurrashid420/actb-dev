"""Dependency injection containers for the actBI service.

Uses ``dependency-injector`` to manage agent lifecycle and configuration.
The container wires settings (Singletons), shared resources (Singletons),
and agents (Factories) so each request gets a fresh agent instance with
shared, expensive resources.

Environment-based configuration:
    - **Production**: settings loaded from AGENT_VIZ_DESIGNER_* / XLAKE_* env vars
    - **Development**: settings from .env / .env.local file
    - **Testing**: override providers with mocks via container.override_providers()

Example usage::

    # Create and wire
    container = AgentsContainer()
    container.wire(modules=["app.api.visualizations.route"])

    # Override for testing
    container.viz_designer_settings.override(
        providers.Object(VisualizationDesignerSettings(debug=True))
    )
"""

from dependency_injector import containers, providers

from agents.viz_designer.agent import VisualizationDesigner
from agents.viz_designer.config import get_viz_designer_settings
from xlake.api.client import create_xlake_client
from xlake.stores.settings import get_xlake_settings


class AgentsContainer(containers.DeclarativeContainer):
    """Container for agent dependencies.

    Manages:
    - Configuration settings (Singletons - loaded once from env)
    - Shared external resources (Singletons - expensive to create)
    - Agent builders (Factories - new instance per request)

    Agents are created as Factories to ensure per-request isolation.
    Settings and clients are Singletons to avoid repeated initialization.
    """

    # =========================================================================
    # Configuration (Singletons - loaded once from environment)
    # =========================================================================

    viz_designer_settings = providers.Singleton(get_viz_designer_settings)
    xlake_settings = providers.Singleton(get_xlake_settings)

    # =========================================================================
    # Shared Resources (Singletons - expensive, thread-safe)
    # =========================================================================

    xlake_client = providers.Singleton(
        create_xlake_client,
        settings=xlake_settings,
    )

    # =========================================================================
    # Agents (Factories - new instance per request for isolation)
    # =========================================================================

    viz_designer = providers.Factory(
        VisualizationDesigner,
        settings=viz_designer_settings,
        xlake_client=xlake_client,
    )
