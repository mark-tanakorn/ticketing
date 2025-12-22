import {
  getAvailableVariables,
  shouldUseVariableInput,
  extractVariablePaths,
  validateVariableReferences,
} from '../variableUtils'

describe('variableUtils', () => {
  describe('extractVariablePaths', () => {
    it('extracts single variable', () => {
      const paths = extractVariablePaths('Hello {{name}}')
      expect(paths).toEqual(['name'])
    })
    
    it('extracts multiple variables', () => {
      const paths = extractVariablePaths('{{greeting}} {{name}}, today is {{date}}')
      expect(paths).toEqual(['greeting', 'name', 'date'])
    })
    
    it('handles nested paths', () => {
      const paths = extractVariablePaths('User: {{user.name}}, Email: {{user.email}}')
      expect(paths).toEqual(['user.name', 'user.email'])
    })
    
    it('returns empty array for no variables', () => {
      const paths = extractVariablePaths('No variables here')
      expect(paths).toEqual([])
    })
    
    it('trims whitespace in variable names', () => {
      const paths = extractVariablePaths('{{ spaced }}')
      expect(paths).toEqual(['spaced'])
    })
  })
  
  describe('shouldUseVariableInput', () => {
    it('returns true if allow_template is explicitly true', () => {
      expect(shouldUseVariableInput({ type: 'boolean', allow_template: true })).toBe(true)
    })
    
    it('returns false if allow_template is explicitly false', () => {
      expect(shouldUseVariableInput({ type: 'string', allow_template: false })).toBe(false)
    })
    
    it('returns true for variable_or_text type', () => {
      expect(shouldUseVariableInput({ type: 'variable_or_text' })).toBe(true)
    })
    
    it('returns true for string with text widget', () => {
      expect(shouldUseVariableInput({ type: 'string', widget: 'text' })).toBe(true)
    })
    
    it('returns true for string with textarea widget', () => {
      expect(shouldUseVariableInput({ type: 'string', widget: 'textarea' })).toBe(true)
    })
    
    it('returns false for string with dropdown widget', () => {
      expect(shouldUseVariableInput({ type: 'string', widget: 'dropdown' })).toBe(false)
    })
    
    it('returns false for string with file_picker widget', () => {
      expect(shouldUseVariableInput({ type: 'string', widget: 'file_picker' })).toBe(false)
    })
    
    it('returns true for plain string without widget', () => {
      expect(shouldUseVariableInput({ type: 'string' })).toBe(true)
    })
  })
  
  describe('getAvailableVariables', () => {
    it('always includes system variables', () => {
      const result = getAvailableVariables([], [], 'node-1', [])
      
      expect(result).toHaveLength(1)
      expect(result[0].nodeName).toBe('🔧 System Variables')
      expect(result[0].fields).toContainEqual({ name: 'current_date', type: 'string' })
    })
    
    it('includes predecessor nodes with sharing enabled', () => {
      const nodes = [
        {
          node_id: 'node-1',
          node_type: 'text_input',
          name: 'Input',
          share_output_to_variables: true,
        },
        {
          node_id: 'node-2',
          node_type: 'processor',
          name: 'Processor',
        },
      ]
      
      const connections = [
        { source_node_id: 'node-1', target_node_id: 'node-2' },
      ]
      
      const nodeDefinitions = [
        {
          node_type: 'text_input',
          output_ports: [{ name: 'output', type: 'string' }],
        },
      ]
      
      const result = getAvailableVariables(nodes, connections, 'node-2', nodeDefinitions)
      
      // Should have system vars + node-1
      expect(result.length).toBeGreaterThan(1)
      expect(result.some(v => v.uniqueKey === 'node-1')).toBe(true)
    })
    
    it('excludes nodes without sharing enabled', () => {
      const nodes = [
        {
          node_id: 'node-1',
          node_type: 'text_input',
          name: 'Input',
          share_output_to_variables: false, // Disabled
        },
        {
          node_id: 'node-2',
          node_type: 'processor',
          name: 'Processor',
        },
      ]
      
      const connections = [
        { source_node_id: 'node-1', target_node_id: 'node-2' },
      ]
      
      const result = getAvailableVariables(nodes, connections, 'node-2', [])
      
      // Should only have system vars
      expect(result).toHaveLength(1)
      expect(result[0].nodeId).toBe('system')
    })
    
    it('handles duplicate node names with numbering', () => {
      const nodes = [
        {
          node_id: 'node-1',
          node_type: 'text_input',
          name: 'Input',
          share_output_to_variables: true,
        },
        {
          node_id: 'node-2',
          node_type: 'text_input',
          name: 'Input', // Duplicate name
          share_output_to_variables: true,
        },
        {
          node_id: 'node-3',
          node_type: 'processor',
          name: 'Processor',
        },
      ]
      
      const connections = [
        { source_node_id: 'node-1', target_node_id: 'node-3' },
        { source_node_id: 'node-2', target_node_id: 'node-3' },
      ]
      
      const nodeDefinitions = [
        {
          node_type: 'text_input',
          output_ports: [{ name: 'text', type: 'string' }],
        },
      ]
      
      const result = getAvailableVariables(nodes, connections, 'node-3', nodeDefinitions)
      
      // Find the input nodes (excluding system)
      const inputVars = result.filter(v => v.nodeId !== 'system')
      
      expect(inputVars).toHaveLength(2)
      // Names should have numbers to distinguish them
      expect(inputVars[0].nodeName).toContain('Input')
      expect(inputVars[1].nodeName).toContain('Input')
    })
  })
  
  describe('validateVariableReferences', () => {
    const mockAvailableVars = [
      {
        nodeName: 'Node 1',
        nodeId: 'node1',
        uniqueKey: 'node-1',
        fields: [{ name: 'output', type: 'string' }],
      },
    ]
    
    it('returns empty array for valid variable reference', () => {
      const config = { source: 'variable', variable_path: 'node1.output' }
      const missing = validateVariableReferences(config, mockAvailableVars)
      
      expect(missing).toEqual([])
    })
    
    it('returns missing path for invalid variable reference', () => {
      const config = { source: 'variable', variable_path: 'node2.invalid' }
      const missing = validateVariableReferences(config, mockAvailableVars)
      
      expect(missing).toEqual(['node2.invalid'])
    })
    
    it('validates template strings', () => {
      const config = { source: 'template', template: 'Value: {{node1.output}}' }
      const missing = validateVariableReferences(config, mockAvailableVars)
      
      expect(missing).toEqual([])
    })
    
    it('finds missing variables in templates', () => {
      const config = { source: 'template', template: 'Invalid: {{missing.var}}' }
      const missing = validateVariableReferences(config, mockAvailableVars)
      
      expect(missing).toEqual(['missing.var'])
    })
    
    it('validates plain string templates', () => {
      const missing = validateVariableReferences('{{node1.output}}', mockAvailableVars)
      expect(missing).toEqual([])
    })
  })
})

