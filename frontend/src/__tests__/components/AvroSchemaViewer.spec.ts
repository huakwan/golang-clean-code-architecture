import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AvroSchemaViewer from '@/components/crud/AvroSchemaViewer.vue'
import type { AvroSchema } from '@/types/crud.types'

const sampleSchema: AvroSchema = {
  type: 'record',
  name: 'user-model',
  fields: [
    { name: 'id', type: 'int' },
    { name: 'email', type: 'string' },
    { name: 'created_at', type: 'datetime' },
  ],
}

describe('AvroSchemaViewer', () => {
  it('renders schema name, field names, and type badges', () => {
    const wrapper = mount(AvroSchemaViewer, {
      props: { schema: sampleSchema },
    })

    expect(wrapper.text()).toContain('user-model')
    expect(wrapper.text()).toContain('id')
    expect(wrapper.text()).toContain('int')
    expect(wrapper.text()).toContain('email')
    expect(wrapper.text()).toContain('string')
    expect(wrapper.text()).toContain('created_at')
    expect(wrapper.text()).toContain('datetime')
  })

  it('shows empty state when schema is null', () => {
    const wrapper = mount(AvroSchemaViewer, {
      props: { schema: null },
    })

    expect(wrapper.text()).toContain('No schema loaded')
  })
})
