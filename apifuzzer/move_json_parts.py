from apifuzzer.utils import pretty_print, get_logger


class JsonSectionAbove:

    def __init__(self, api_definition, section_to_up='schema'):
        self.logger = get_logger(f'{self.__class__.__name__}-{section_to_up}')
        self.api_definition = api_definition
        self.section_to_up = section_to_up

    def _resolve(self, data):
        schema_fount = False
        self.logger.debug(f'Processing {pretty_print(data, 50)}')
        if isinstance(data, dict):
            return_data = dict()
            for key, value in data.items():
                self.logger.debug(f'Checking {key} - {pretty_print(value, 50)}')
                if key == self.section_to_up and value:
                    schema_fount = True
                    if isinstance(value, dict):
                        return_data.update(value)
                    else:
                        return_data = value
                    self.logger.debug(f'Processed {key} -> {pretty_print(return_data)}')
                elif isinstance(value, dict):
                    self.logger.debug(f'Process dict {key}')
                    return_data[key] = self.resolve(value)
                elif isinstance(value, list):
                    if not return_data.get(key):
                        return_data[key] = list()
                    for iter in range(len(value)):
                        self.logger.debug(f'Process {key} list elem: {iter}')
                        return_data[key].append(self.resolve(data=value[iter]))

                else:
                    return_data[key] = value
                self.logger.debug(f'Processed: {key} -> {pretty_print(return_data, 100)}')
        else:
            return_data = data
        return [return_data, schema_fount]

    def resolve(self, data=None):
        self.logger.info('Resolving schema references')
        if data is None:
            data = self.api_definition
        resolved_in_this_iteration = True

        iteration = 1
        while resolved_in_this_iteration:
            self.logger.debug(f'{iteration} resolving reference')
            data, resolved_in_this_iteration = self._resolve(data)
            iteration += 1
        return data
