#!/usr/bin/python
# -- Content-Encoding: UTF-8 --

# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------

ENDPOINT_LISTENER_SCOPE = "endpoint.listener.scope"

# ------------------------------------------------------------------------------

IMPORT_REGISTRATION = 1
""" Add an import registration. """

EXPORT_REGISTRATION = 2
""" Add an export registration. """

EXPORT_UNREGISTRATION = 3
""" Remove an export registration """

IMPORT_UNREGISTRATION = 4
""" Remove an import registration. """

IMPORT_ERROR = 5
""" A fatal importing error occurred. """

EXPORT_ERROR = 6
""" A fatal exporting error occurred. """

EXPORT_WARNING = 7
""" A problematic situation occurred, the export is still active. """

IMPORT_WARNING = 8
""" A problematic situation occurred, the import is still active. """

EXPORT_TYPES = (EXPORT_REGISTRATION, EXPORT_UNREGISTRATION,
                EXPORT_ERROR, EXPORT_WARNING)
""" Export notification types """


# --- Remote service admin listener interface ---

class RemoteServiceAdminListener(object):
    """
    A RemoteServiceAdminEvent listener is notified synchronously of any export
    or import registrations and unregistrations.
    """
    def remoteAdminEvent(self, event):
        """
        Receive notification of any export or import registrations and
        unregistrations as well as errors and warnings.

        :param event: The RemoteServiceAdminEvent object.
        """
        pass


# ------------------------------------------------------------------------------

class ImportReference(object):
    """
    An Import Reference associates an active proxy service to a remote endpoint.
    """
    def __init__(self, endpoint, reference):
        """
        Sets up members
        """
        self.endpoint = endpoint
        self.reference = reference


    def get_imported_endpoint(self):
        """
        :return: The Endpoint Description for the remote endpoint.
                 Must be null when the service is no longer imported.
        """
        return self.endpoint


    def get_imported_service(self):
        """
        :return: The Service Reference to the proxy for the endpoint.
                 Must be null when the service is no longer imported.
        """
        return self.reference


class ImportRegistration(object):
    """
    An Import Registration associates an active proxy service to a remote
    endpoint. It is created with the
    RemoteServiceAdmin.importService(EndpointDescription) method.
    """
    def __init__(self, reference, exception=None):
        """
        Sets up members
        """
        self.exception = exception
        self.reference = reference


    def close(self):
        """
        Close this Import Registration. This must close the connection to the
        endpoint and unregister the proxy. After this method returns, all
        methods must return null.
        """
        self.exception = None
        self.reference = None


    def get_exception(self):
        """
        Return the exception for any error during the import process.

        :return: The exception that occurred during the initialization of this
                 registration or null if no exception occurred.
        """
        return self.exception


    def get_import_reference(self):
        """
        :return: The Import Reference for this registration.
        """
        return self.reference

# ------------------------------------------------------------------------------

class ExportReference(object):
    """
    An Export Reference associates a service with a local endpoint.
    """
    def __init__(self, endpoint, reference):
        """
        Sets up members

        :param endpoint: An endpoint description
        :param reference: A local service reference
        """
        self.endpoint = endpoint
        self.reference = reference

    def get_exported_endpoint(self):
        """
        :return: The endpoint description
        """
        return self.endpoint


    def get_exported_service(self):
        """
        :return: A service reference
        """
        return self.reference


class ExportRegistration(object):
    """
    An Export Registration associates a service to a local endpoint.
    It is created with the
    RemoteServiceAdmin.exportService(ServiceReference,Map) method.
    """
    def __init__(self, reference, exception=None):
        """
        Sets up members
        """
        self.reference = reference
        self.exception = exception


    def close(self):
        """
        Delete the local endpoint and disconnect any remote distribution
        providers. After this method returns, all methods must return null.
        """
        self.reference = None
        self.exception = None


    def getException(self):
        """
        Return the exception for any error during the export process.

        :return: The exception that occurred during the initialization of this
                 registration or null if no exception occurred.
        """
        return self.exception


    def getExportReference(self):
        """
        :return: The Export Reference for this registration.
        """
        return self.reference

# ------------------------------------------------------------------------------

class RemoteServiceAdminEvent(object):
    """
    Provides the event information for a Remote Service Admin event.
    """
    def __init__(self, evt_type, source, reference, exception):
        """
        :param evt_type: The event type
        :param source: The source bundle, must not be None
        :param export: If True, the reference is an export one, else False
        :param reference: The import or export refernece, can't be None
        :param exception: Any exception encountered, can be None
        """
        self.evt_type = evt_type
        self.source = source
        self.reference = reference
        self.exception = exception

        self.export = source in EXPORT_TYPES


    def getException(self):
        """
        Return the exception for this event.

        :return: The exception or null.
        """
        return self.exception


    def getExportReference(self):
        """
        Return the Export Reference for this event.

        :return: The Export Reference or null.
        """
        if self.export:
            return self.reference


    def getImportReference(self):
        """
        Return the Import Reference for this event.

        :return: The Import Reference or null.
        """
        if not self.export:
            return self.reference


    def getSource(self):
        """
        Return the bundle source of this event.

        :return: The bundle source of this event.
        """
        return self.source


    def getType(self):
        """
        Return the type of this event

        :return: The type of this event.
        """
        return self.evt_type
