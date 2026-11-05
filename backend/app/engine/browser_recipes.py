"""Typed browser recipes are bounded ordinary workflows, not a second execution language."""
import copy,json
from typing import Annotated
from jsonschema import Draft202012Validator
from pydantic import Field,model_validator
from .browser_contract import Contract,VersionedContract,Identifier,ARGUMENT_MODELS,Extract
from .state_schema import state_schema
from .templating import render_args
from ..core.errors import AppError

MAX_ACTIONS=20
MAX_INPUT=16*1024
MAX_OUTPUT=256*1024
MARKER='_browser_recipe'


class Recipe(VersionedContract):
    connection_id: Identifier
    inputs: Annotated[list[Identifier],Field(min_length=1,max_length=20)]
    outputs: Annotated[list[Identifier],Field(min_length=1,max_length=20)]

    @model_validator(mode='after')
    def unique_fields(self):
        if len(set(self.inputs))!=len(self.inputs) or len(set(self.outputs))!=len(self.outputs) or set(self.inputs)&set(self.outputs):raise ValueError('Recipe fields')
        return self


class Target(Contract):
    observation_field: Identifier
    role: Annotated[str,Field(min_length=1,max_length=80)]
    text: Annotated[str,Field(min_length=1,max_length=1000)]|None=None


def parsed(wf):
    if 'browser_recipe' not in wf:return None
    try:
        recipe=Recipe.model_validate(wf['browser_recipe'])
        fields={field['name']:field.get('type','string') for field in wf.get('state') or []}
        if any(fields.get(name) not in {'string','integer','number','boolean'} for name in recipe.inputs):raise ValueError('Input fields')
        nodes=wf.get('nodes') or [];edges=wf.get('edges') or []
        if len(nodes)>MAX_ACTIONS+2 or not 3<=len(nodes) or len(edges)!=len(nodes)-1:raise ValueError('Recipe bounds')
        starts=[node for node in nodes if node.get('type')=='start'];ends=[node for node in nodes if node.get('type')=='end']
        if len(starts)!=1 or len(ends)!=1:raise ValueError('Recipe endpoints')
        by_id={node['id']:node for node in nodes};current=starts[0]['id'];seen=set();written=set();observed=set()
        while current not in seen:
            seen.add(current);node=by_id[current];kind=node.get('type');data=node.get('data') or {}
            if kind not in {'start','end','mcp'}:raise ValueError('Recipe action')
            if kind=='mcp':
                operation=data.get('tool');arguments=data.get('arguments',{})
                if data.get('server_id')!=recipe.connection_id or operation not in ARGUMENT_MODELS or not isinstance(arguments,dict):raise ValueError('Recipe connection/action')
                if data.get('retry') or data.get('cache_ttl'):raise ValueError('Recipe retry/cache')
                output=data.get('output_field')
                if output in recipe.inputs or fields.get(output)!='object' or output in written:raise ValueError('Recipe output')
                written.add(output)
                if operation in {'click','fill'}:
                    target=Target.model_validate(data.get('target'))
                    if target.text is None:raise ValueError('Effect target requires literal text')
                    if target.observation_field not in observed:raise ValueError('Earlier observation required')
                    if set(arguments)-({'value'} if operation=='fill' else set()):raise ValueError('Target references are derived')
                    if operation=='fill' and 'value' not in arguments:raise ValueError('Fill value required')
                elif operation=='extract':
                    targets=data.get('targets')
                    if not isinstance(targets,dict) or not 1<=len(targets)<=20 or arguments:raise ValueError('Extraction targets')
                    Extract(observation_id='fixture',fields={name:'fixture' for name in targets})
                    for target in targets.values():
                        selected=Target.model_validate(target)
                        if selected.observation_field not in observed:raise ValueError('Earlier observation required')
                    # One observation per extract is enforced at runtime too.
                    if len({item['observation_field'] for item in targets.values()})!=1:raise ValueError('Single extract observation')
                else:
                    if data.get('target') or data.get('targets'):raise ValueError('Unexpected target')
                    if operation!='navigate' and arguments:raise ValueError('Read arguments')
                    if operation=='navigate' and set(arguments)!={'url'}:raise ValueError('Navigate URL')
                if operation in {'navigate','snapshot'}:observed.add(output)
            outgoing=[edge for edge in edges if edge.get('source')==current]
            if kind=='end':
                if outgoing:raise ValueError('End edge')
                break
            if len(outgoing)!=1 or outgoing[0].get('label') or outgoing[0].get('target') not in by_id:raise ValueError('Recipe must be linear')
            current=outgoing[0]['target']
        if len(seen)!=len(nodes) or not set(recipe.outputs)<=written:raise ValueError('Recipe reachability/outputs')
        return recipe
    except (ValueError,TypeError,KeyError,AttributeError):raise AppError('BROWSER_RECIPE_INVALID') from None


def errors(wf):
    try:parsed(wf);return []
    except AppError:
        from .issues import Issue
        return [Issue('BROWSER_RECIPE_INVALID')]


def input_schema(wf):
    recipe=parsed(wf)
    if recipe is None:return state_schema(wf,'Input')
    props=state_schema(wf)['properties']
    return {'type':'object','additionalProperties':False,'required':recipe.inputs,
        'properties':{name:{**props[name],**({'minLength':1,'maxLength':2048} if props[name]['type']=='string' else {})} for name in recipe.inputs}}


def validate_input(wf,value):
    if parsed(wf) is None:return
    try:
        if len(json.dumps(value,ensure_ascii=False,allow_nan=False).encode())>MAX_INPUT or not Draft202012Validator(input_schema(wf)).is_valid(value):raise ValueError()
    except (ValueError,TypeError,UnicodeError,RecursionError):raise AppError('MCP_ARGUMENT_INVALID',name='arguments',type='closed typed recipe input') from None


def prepare(wf):
    """Strip client-supplied execution markers; derive one group from a validated root recipe."""
    if 'browser_recipe' not in wf and not any(MARKER in (node.get('data') or {}) for node in wf.get('nodes') or []):return wf
    result=copy.deepcopy(wf);recipe=parsed(result)
    for node in result.get('nodes') or []:
        data=node.get('data') or {};data.pop(MARKER,None)
        if recipe is not None and node.get('type')=='mcp':data[MARKER]=True
    return result


def select(target,state):
    selected=Target.model_validate(target);result=state.get(selected.observation_field) or {}
    observation=result.get('observation') or {}
    elements=observation.get('elements') or []
    matches=[element for element in elements if element.get('role')==selected.role and (selected.text is None or element.get('text')==selected.text)]
    if result.get('status')!='confirmed' or len(matches)!=1 or not observation.get('observation_id'):raise AppError('MCP_TOOL_FAILED',reason='Browser recipe target is missing or ambiguous')
    return observation['observation_id'],matches[0]['element_id']


def arguments(data,state):
    values=render_args(data.get('arguments') or {},state)
    if data.get('tool') in {'click','fill'}:
        observation,element=select(data['target'],state)
        return {**values,'observation_id':observation,'element_id':element}
    if data.get('tool')=='extract':
        fields={};observation=None
        for name,target in data['targets'].items():
            current,element=select(target,state)
            if observation is not None and observation!=current:raise AppError('MCP_TOOL_FAILED',reason='Browser recipe observation changed')
            observation=current;fields[name]=element
        return {'observation_id':observation,'fields':fields}
    return values


def outputs(wf,state):
    recipe=parsed(wf)
    if recipe is None:return state
    value={name:state.get(name) for name in recipe.outputs}
    if any(not isinstance(item,dict) for item in value.values()) or len(json.dumps(value,ensure_ascii=False,allow_nan=False).encode())>MAX_OUTPUT:
        raise AppError('MCP_TOOL_FAILED',reason='Browser recipe output is missing or exceeds its bound')
    return value
