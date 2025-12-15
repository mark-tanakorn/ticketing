import { 
  groupNodesByCategory, 
  getCategoryIcon, 
  getNodeIcon 
} from '../nodeUtils'

describe('nodeUtils', () => {
  describe('groupNodesByCategory', () => {
    it('groups nodes by category correctly', () => {
      const nodes = [
        { node_type: 'trigger1', name: 'Trigger A', category: 'triggers', description: 'Test trigger' },
        { node_type: 'trigger2', name: 'Trigger B', category: 'triggers', description: 'Another trigger' },
        { node_type: 'action1', name: 'Action A', category: 'actions', description: 'Test action' },
      ]
      
      const grouped = groupNodesByCategory(nodes)
      
      expect(grouped).toHaveLength(2)
      expect(grouped[0].name).toBe('Triggers')
      expect(grouped[0].nodes).toHaveLength(2)
      expect(grouped[1].name).toBe('Actions')
      expect(grouped[1].nodes).toHaveLength(1)
    })
    
    it('preserves node ports', () => {
      const nodes = [
        {
          node_type: 'http_request',
          name: 'HTTP Request',
          category: 'actions',
          input_ports: [{ name: 'url', type: 'string' }],
          output_ports: [{ name: 'response', type: 'json' }],
        },
      ]
      
      const grouped = groupNodesByCategory(nodes)
      
      expect(grouped[0].nodes[0].input_ports).toHaveLength(1)
      expect(grouped[0].nodes[0].output_ports).toHaveLength(1)
    })
    
    it('capitalizes category names', () => {
      const nodes = [
        { node_type: 'node1', name: 'Node', category: 'communication', description: 'Test' },
      ]
      
      const grouped = groupNodesByCategory(nodes)
      
      expect(grouped[0].name).toBe('Communication')
    })
  })
  
  describe('getCategoryIcon', () => {
    it('returns correct icon for known categories', () => {
      expect(getCategoryIcon('triggers')).toBe('fa-solid fa-bolt')
      expect(getCategoryIcon('actions')).toBe('fa-solid fa-play')
      expect(getCategoryIcon('ai')).toBe('fa-solid fa-brain')
      expect(getCategoryIcon('communication')).toBe('fa-solid fa-paper-plane')
    })
    
    it('returns default icon for unknown category', () => {
      expect(getCategoryIcon('unknown')).toBe('fa-solid fa-cube')
    })
    
    it('is case insensitive', () => {
      expect(getCategoryIcon('TRIGGERS')).toBe('fa-solid fa-bolt')
      expect(getCategoryIcon('TrIgGeRs')).toBe('fa-solid fa-bolt')
    })
  })
  
  describe('getNodeIcon', () => {
    it('returns icon with color and bgColor', () => {
      const result = getNodeIcon('ai')
      
      expect(result.icon).toBe('fa-solid fa-brain')
      expect(result.color).toBe('#9333ea')
      expect(result.bgColor).toContain('rgba')
    })
    
    it('returns default for unknown category', () => {
      const result = getNodeIcon('unknown')
      
      expect(result.icon).toBe('fa-solid fa-cube')
      expect(result.color).toBe('#4b5563')
    })
  })
})

