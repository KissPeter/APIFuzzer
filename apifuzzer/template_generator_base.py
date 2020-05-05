from apifuzzer.utils import set_class_logger


@set_class_logger
class TemplateGenerator(object):
    """
    Skeleton template generator
    """

    def process_api_resources(self):
        """
        This method processes the API definition
        """
        pass

    def compile_base_url(self, alternate_url):
        """
        This method finalizes the url where the request should be sent to
        :param alternate_url: alternative url if the one set in API definition is overwritten
        :type alternate_url: str
        :return: url
        :rtype: str
        """
        pass
