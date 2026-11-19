import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DynamicFormModal from '@/components/crud/DynamicFormModal.vue'
import type { AvroSchema } from '@/types/crud.types'

const sampleSchema: AvroSchema = {
  type: 'record',
  name: 'sample-entity',
  fields: [
    { name: 'id', type: 'int' },
    { name: 'email', type: 'string' },
    { name: 'age', type: 'int' },
    { name: 'score', type: 'float' },
    { name: 'is_active', type: 'boolean' },
    { name: 'published_at', type: 'datetime' },
    { name: 'metadata', type: 'map' },
    {
      name: 'user',
      type: 'users',
      fields: { type: 'record', name: 'users', fields: [{ name: 'id', type: 'int' }] },
    },
    { name: 'created_at', type: 'datetime' },
    { name: 'updated_at', type: 'datetime' },
  ],
}

describe('DynamicFormModal', () => {
  it('renders appropriate inputs from Avro types and excludes read-only and nested fields', () => {
    const wrapper = mount(DynamicFormModal, {
      props: {
        open: true,
        mode: 'create',
        schema: sampleSchema,
        entityLabel: 'Sample Entity',
      },
    })

    expect(wrapper.find('[data-testid="field-id"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="field-created_at"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="field-updated_at"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="field-user"]').exists()).toBe(false)

    expect(wrapper.find('[data-testid="field-email"]').attributes('type')).toBe('email')
    expect(wrapper.find('[data-testid="field-age"]').attributes('type')).toBe('number')
    expect(wrapper.find('[data-testid="field-score"]').attributes('type')).toBe('number')
    expect(wrapper.find('[data-testid="field-is_active"]').attributes('type')).toBe('checkbox')
    expect(wrapper.find('[data-testid="field-published_at"]').attributes('type')).toBe(
      'datetime-local',
    )
    expect(wrapper.find('textarea[data-testid="field-metadata"]').exists()).toBe(true)
  })

  it('coerces typed values and emits submit payload on create', async () => {
    const wrapper = mount(DynamicFormModal, {
      props: {
        open: true,
        mode: 'create',
        schema: sampleSchema,
        entityLabel: 'Sample Entity',
      },
    })

    await wrapper.find('[data-testid="field-email"]').setValue('alice@example.com')
    await wrapper.find('[data-testid="field-age"]').setValue('29')
    await wrapper.find('[data-testid="field-score"]').setValue('9.5')
    await wrapper.find('[data-testid="field-is_active"]').setValue(true)
    await wrapper.find('[data-testid="field-metadata"]').setValue('{"role":"admin"}')

    await wrapper.find('form').trigger('submit.prevent')

    const emitted = wrapper.emitted('submit')
    expect(emitted).toHaveLength(1)
    expect(emitted?.[0]?.[0]).toEqual({
      email: 'alice@example.com',
      age: 29,
      score: 9.5,
      is_active: true,
      metadata: { role: 'admin' },
    })
  })

  it('pre-populates fields in edit mode and emits updated values', async () => {
    const wrapper = mount(DynamicFormModal, {
      props: {
        open: true,
        mode: 'edit',
        schema: sampleSchema,
        entityLabel: 'Sample Entity',
        initialData: {
          id: 42,
          email: 'alice@example.com',
          age: 30,
          score: 8.2,
          is_active: true,
          metadata: { team: 'core' },
        },
      },
    })

    expect((wrapper.find('[data-testid="field-email"]').element as HTMLInputElement).value).toBe(
      'alice@example.com',
    )
    expect((wrapper.find('[data-testid="field-age"]').element as HTMLInputElement).value).toBe('30')

    await wrapper.find('[data-testid="field-age"]').setValue('31')
    await wrapper.find('form').trigger('submit.prevent')

    const emitted = wrapper.emitted('submit')
    expect(emitted).toHaveLength(1)
    expect(emitted?.[0]?.[0]).toMatchObject({
      email: 'alice@example.com',
      age: 31,
      score: 8.2,
      is_active: true,
      metadata: { team: 'core' },
    })
  })

  it('shows validation error and blocks submit when JSON map field is invalid', async () => {
    const wrapper = mount(DynamicFormModal, {
      props: {
        open: true,
        mode: 'create',
        schema: sampleSchema,
        entityLabel: 'Sample Entity',
      },
    })

    await wrapper.find('[data-testid="field-metadata"]').setValue('{invalid json')
    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(wrapper.text()).toContain('Invalid JSON')
  })
})
