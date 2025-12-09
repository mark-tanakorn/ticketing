import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import PasswordInput from '../PasswordInput'

describe('PasswordInput Component', () => {
  it('renders password input field', () => {
    render(
      <PasswordInput
        value=""
        onChange={() => {}}
        placeholder="Enter password"
      />
    )
    
    const input = screen.getByPlaceholderText('Enter password')
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('type', 'password')
  })
  
  it('toggles password visibility when button clicked', async () => {
    const user = userEvent.setup()
    
    render(
      <PasswordInput
        value="secret123"
        onChange={() => {}}
      />
    )
    
    const input = screen.getByDisplayValue('secret123')
    expect(input).toHaveAttribute('type', 'password')
    
    // Find and click the toggle button
    const toggleButton = screen.getByRole('button')
    await user.click(toggleButton)
    
    // Should now be visible
    expect(input).toHaveAttribute('type', 'text')
  })
  
  it('calls onChange when value changes', async () => {
    const user = userEvent.setup()
    const mockOnChange = jest.fn()
    
    render(
      <PasswordInput
        value=""
        onChange={mockOnChange}
        placeholder="Enter password"
      />
    )
    
    const input = screen.getByPlaceholderText('Enter password')
    await user.type(input, 'test')
    
    expect(mockOnChange).toHaveBeenCalled()
  })
})

