import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DynamicDataTable from '@/components/crud/DynamicDataTable.vue'
import type { AvroSchema } from '@/types/crud.types'

const sampleSchema: AvroSchema = {
  type: 'record',
  name: 'user-model',
  fields: [
    { name: 'id', type: 'int' },
    { name: 'email', type: 'string' },
    { name: 'first_name', type: 'string' },
  ],
}

const sampleItems = [
  { id: 1, email: 'alice@example.com', first_name: 'Alice' },
  { id: 2, email: 'bob@example.com', first_name: 'Bob' },
]

describe('DynamicDataTable', () => {
  it('renders columns from Avro schema and row values', () => {
    const wrapper = mount(DynamicDataTable, {
      props: {
        schema: sampleSchema,
        items: sampleItems,
        loading: false,
      },
    })

    const headers = wrapper.findAll('th').map((th) => th.text())
    expect(headers).toContain('id')
    expect(headers).toContain('email')
    expect(headers).toContain('first_name')

    expect(wrapper.text()).toContain('alice@example.com')
    expect(wrapper.text()).toContain('bob@example.com')
  })

  it('emits inspect event with record id when View button is clicked', async () => {
    const wrapper = mount(DynamicDataTable, {
      props: {
        schema: sampleSchema,
        items: sampleItems,
        loading: false,
      },
    })

    const viewButtons = wrapper.findAll('button[data-testid="inspect-row"]')
    expect(viewButtons).toHaveLength(2)
    await viewButtons[0].trigger('click')

    expect(wrapper.emitted('inspect')).toEqual([[1]])
  })

  it('shows Edit and Delete buttons based on canUpdate and canDelete props and emits events', async () => {
    const wrapper = mount(DynamicDataTable, {
      props: {
        schema: sampleSchema,
        items: sampleItems,
        loading: false,
        canUpdate: true,
        canDelete: true,
      },
    })

    const editButtons = wrapper.findAll('button[data-testid="edit-row"]')
    const deleteButtons = wrapper.findAll('button[data-testid="delete-row"]')
    expect(editButtons).toHaveLength(2)
    expect(deleteButtons).toHaveLength(2)

    await editButtons[0].trigger('click')
    await deleteButtons[1].trigger('click')

    expect(wrapper.emitted('edit')).toEqual([[sampleItems[0]]])
    expect(wrapper.emitted('delete')).toEqual([[2]])
  })

  it('hides Edit button when canUpdate is false while keeping Delete when canDelete is true', () => {
    const wrapper = mount(DynamicDataTable, {
      props: {
        schema: sampleSchema,
        items: sampleItems,
        loading: false,
        canUpdate: false,
        canDelete: true,
      },
    })

    expect(wrapper.findAll('button[data-testid="edit-row"]')).toHaveLength(0)
    expect(wrapper.findAll('button[data-testid="delete-row"]')).toHaveLength(2)
  })
})
