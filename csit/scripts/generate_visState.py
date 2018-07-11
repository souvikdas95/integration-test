# SPDX-License-Identifier: EPL-1.0
##############################################################################
# Copyright (c) 2018 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v1.0
# which accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v10.html
##############################################################################
import yaml
import copy

import json


dc = copy.deepcopy


def p(x):
    print(json.dumps(x, indent=4, sort_keys=True))


class visState:
    def __init__(self):
        self.content = {
            'title': None,
            'type': None,
            'params': {
                'type': None,
                'grid': {
                    'categoryLines': False,
                    'style': {
                        'color': '#eee'
                    }
                },
                'categoryAxes': None,
                'valueAxes': None,
                'seriesParams': None,
                'addTooltip': True,
                'addLegend': True,
                'legendPosition': 'right',
                'times': [],
                'addTimeMarker': False
            },
            'aggs': None
        }

    def create(self, config):
        temp = self.content
        temp['title'] = config['title']
        temp['type'] = temp['params']['type'] = config['type']

        cat = categoryAxes()
        temp['params']['categoryAxes'] = [dc(
            cat.create()) for i in range(config['num_cat_axes'])]

        val = ValueAxes()
        temp['params']['valueAxes'] = [dc(val.create(position=i['position'],
                                                     title=i['title']))
                                       for _, i in
                                       config['value_axes'].items()]

        agg = aggs()

        temp['aggs'] = [dc(agg.create(field=i['field'],
                                      custom_label=i['custom_label'],
                                      schema=i['schema']))
                        for _, i in
                        config['aggs'].items()]

        temp['params']['seriesParams'] = [seriesParams(i['data_type'],
                                                       i['mode'],
                                                       i['label'],
                                                       i['agg_id'],
                                                       i['value_axis'])
                                          .create()
                                          for _, i in
                                          config['seriesParams'].items()]

        return temp


class categoryAxes:
    def __init__(self):
        self.content = {
            'id': None,
            'type': 'category',
            'position': 'bottom',
            'show': True,
            'style': {},
            'scale': {
                'type': 'linear'
            },
            'labels': {
                'show': True,
                'truncate': 100
            },
            'title': {}
        }
        self.counter = 0

    def create(self):
        self.counter += 1
        temp = dc(self.content)
        temp['id'] = 'CategoryAxis-{}'.format(self.counter)
        return temp


class ValueAxes:
    def __init__(self):
        self.content = {
            'id': None,
            'name': None,
            'type': 'value',
            'position': 'left',
            'show': True,
            'style': {},
            'scale': {
                'type': 'linear',
                'mode': 'normal'
            },
            'labels': {
                'show': True,
                'rotate': 0,
                'filter': False,
                'truncate': 100
            },
            'title': {
                'text': None
            }
        }
        self.counter = 0

    def create(self, position='left', title='Value'):
        self.counter += 1
        temp = dc(self.content)
        temp['id'] = 'ValueAxis-{}'.format(self.counter)
        if position == 'left':
            temp['name'] = 'LeftAxis-{}'.format(self.counter)
        elif position == 'right':
            temp['name'] = 'RightAxis-{}'.format(self.counter)
        else:
            # raise ValueError('Not one of left or right')
            # assuming default
            temp['name'] = 'LeftAxis-{}'.format(self.counter)

        temp['title']['text'] = title

        return temp


class seriesParams:
    def __init__(self, data_type, mode, label, agg_id, value_axis):
        self.content = {
            'show': True,
            'type': data_type,
            'mode': mode,
            'data': {
                'label': label,
                'id': str(agg_id)
            },
            'valueAxis': 'ValueAxis-{}'.format(value_axis),
            'drawLinesBetweenPoints': True,
            'showCircles': True
        }

    def create(self):
        return self.content


class aggs:
    def __init__(self):
        self.content = {
            'id': None,
            'enabled': True,
            'type': None,
            'schema': None,
            'params': {
                'field': None,
                'customLabel': None
            }
        }
        self.counter = 0

    def create(self, field, custom_label, schema):
        self.counter += 1
        temp = dc(self.content)
        temp['id'] = str(self.counter)
        temp['params']['field'] = field
        temp['params']['customLabel'] = custom_label
        temp['schema'] = schema
        if schema == 'metric':
            temp['type'] = 'max'
            return temp
        elif schema == 'segment':
            temp['type'] = 'terms'
            temp['params']['size'] = 20  # default
            temp['params']['order'] = 'asc'
            temp['params']['orderBy'] = '_term'
        return temp


# generate takes both the template config and project specific config and
# parses and organizes as much info available from that and
# generates an intermediate format first which
# contains all necessary info to deterministically create the visState to
# be sent to Kibana. Hence, any error occuring in the visualizaton side
# must first be checked by looking at the intermediate format.

def generate(dash_config, viz_config):

    format = {
        "type": None,
        "value_axes": {},
        "seriesParams": {},
        "index_pattern": None,
        "desc": None,
        "id": None,
        "aggs": {},
        "title": None,
        "num_cat_axes": None
    }

    value_axes_format = {
        "index": {
            "position": None,
            "title": None
        }
    }

    seriesParams_format = {
        "index": {
            "value_axis": None,
            "data_type": None,
            "mode": None,
            "label": None,
            "agg_id": None
        }
    }

    aggs_format = {
        "index": {
            "custom_label": None,
            "field": None,
            "schema": None
        }
    }

    # all general description must be present in either of the config files
    for config in [viz_config, dash_config]:
        general_fields = ['type', 'index_pattern',
                          'num_cat_axes', 'title', 'desc', 'id']
        for i in general_fields:
            try:
                format[i] = config[i]
            except KeyError as e:
                pass

    # setting any default values if available
    mappings = {'value_axes': value_axes_format,
                'seriesParams': seriesParams_format, 'aggs': aggs_format}
    for index, container in mappings.items():
        try:
            default_values = viz_config[index]['default']
            for i in default_values:
                container['index'][i] = default_values[i]
        except Exception:
            pass

    value_axes_counter = 1
    for m in viz_config['value_axes']:
        if m != "default":
            temp = dc(value_axes_format)
            temp[str(value_axes_counter)] = temp['index']
            for i in ['position', 'title']:
                try:
                    temp[str(value_axes_counter)
                         ][i] = viz_config['value_axes'][m][i]
                except KeyError:
                    pass
            format['value_axes'].update(temp)
            value_axes_counter += 1

    seriesParams_counter = 1
    seriesParams_fields = ['value_axis',
                           'data_type', 'mode', 'label', 'agg_id']
    try:
        for m in viz_config['seriesParams']:
            if m != 'default':
                temp = dc(seriesParams_format)
                temp[str(seriesParams_counter)] = temp['index']
                for i in seriesParams_fields:
                    try:
                        temp[str(seriesParams_counter)
                             ][i] = viz_config['seriesParams'][m][i]
                    except KeyError:
                        pass
                format['seriesParams'].update(temp)
                seriesParams_counter += 1
    except KeyError:
        pass

    agg_counter = 1
    try:
        for m in viz_config['aggs']:
            if m != 'default':
                temp = dc(aggs_format)
                temp[str(agg_counter)] = temp['index']
                for i in ['field', 'custom_label', 'schema']:
                    try:
                        temp[str(agg_counter)][i] = viz_config['aggs'][m][i]
                    except KeyError:
                        pass
                format['aggs'].update(temp)
                agg_counter += 1
    except KeyError:
        pass

    configs = []
    try:
        viz_config['series']
        configs.append(viz_config)
    except KeyError:
        pass

    try:
        dash_config['y-axis']['series']
        configs.append(dash_config['y-axis'])
    except KeyError:
        pass

    for config in configs:
        try:
            value_axes_counter = 1
            for key in config['value_axes']:

                value_axes_temp = dc(value_axes_format)
                value_axes_temp[str(value_axes_counter)
                                ] = value_axes_temp['index']

                for index in ['position', 'title']:
                    try:
                        value_axes_temp[str(
                            value_axes_counter)][index] = \
                            config['value_axes'][key][index]
                    except KeyError as e:
                        pass
                format['value_axes'].update(value_axes_temp)
                value_axes_counter += 1

        except KeyError as e:
            pass

        try:
            for key in config['series']:
                try:
                    # check if this key is present or not
                    config['series'][key]['not_in_seriesParams']
                except KeyError:
                    seriesParams_temp = dc(seriesParams_format)
                    seriesParams_temp[str(
                        seriesParams_counter)] = seriesParams_temp['index']
                    for index in ['value_axis', 'data_type', 'mode', 'label']:
                        try:
                            seriesParams_temp[str(
                                seriesParams_counter)][index] = \
                                config['series'][key][index]
                        except KeyError as e:
                            pass
                    seriesParams_temp[str(
                        seriesParams_counter)]['agg_id'] = agg_counter
                    format['seriesParams'].update(seriesParams_temp)
                    seriesParams_counter += 1
                finally:
                    agg_temp = dc(aggs_format)
                    agg_temp[str(agg_counter)] = agg_temp['index']
                    for index in ['field', 'schema']:
                        try:
                            agg_temp[str(agg_counter)
                                     ][index] = config['series'][key][index]
                        except KeyError as e:
                            pass
                    agg_temp[str(
                        agg_counter)]['custom_label'] = \
                        config['series'][key]['label']
                    format['aggs'].update(agg_temp)
                    agg_counter += 1
        except KeyError as e:
            print("required fields are empty!")

    # to remove the default template index
    for i in ['value_axes', 'seriesParams', 'aggs']:
        try:
            format[i].pop('index')
        except KeyError:
            # print("No default index found")
            pass

    if not config_validator(format):
        raise ValueError('Missing required field values')

    p(format)

    vis = visState()
    generated_visState = vis.create(format)

    # checking incase there are None values \
    # in the format indicating missing fields

    if not config_validator(generated_visState):
        raise KeyError('required fields are missing values!')
    return format, generated_visState


# Check the generated format if it contains any key with None
# as it's value which indicates incomplete information
def config_validator(val):
    flag = True
    for _, i in val.items():
        if isinstance(i, dict):
            flag = config_validator(i)
        if i is None:
            return False
    return flag


if __name__ == '__main__':
    with open('viz.yaml', 'r') as f:
        viz_config = yaml.safe_load(f)

    with open('dashboard.yaml', 'r') as f:
        dash_config = yaml.safe_load(f)

    generate(dash_config['dashboard']['viz'][2],
             viz_config['opendaylight-test-performance'])
    # generate(dash_config['dashboard']['viz'][3],viz_config['opendaylight-test-performance'])
    # generate(dash_config['dashboard']['viz'][1],viz_config['opendaylight-test-feature'])
