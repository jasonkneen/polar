'use client'

import revalidate from '@/app/actions'
import { useCustomer, useCustomerPaymentMethods } from '@/hooks/queries'
import { createClientSideAPI } from '@/utils/client'
import { schemas } from '@polar-sh/client'
import Button from '@polar-sh/ui/components/atoms/Button'
import { Separator } from '@polar-sh/ui/components/ui/separator'
import { Modal } from '../Modal'
import { useModal } from '../Modal/useModal'
import { Well, WellContent, WellHeader } from '../Shared/Well'
import { AddPaymentMethodModal } from './AddPaymentMethodModal'
import EditBillingDetails from './EditBillingDetails'
import PaymentMethod from './PaymentMethod'

interface CustomerPortalSettingsProps {
  organization: schemas['Organization']
  customerSessionToken?: string
}

export const CustomerPortalSettings = ({
  customerSessionToken,
}: CustomerPortalSettingsProps) => {
  const api = createClientSideAPI(customerSessionToken)

  const {
    isShown: isAddPaymentMethodModalOpen,
    hide: hideAddPaymentMethodModal,
    show: showAddPaymentMethodModal,
  } = useModal()
  const { data: customer } = useCustomer(api)
  const { data: paymentMethods } = useCustomerPaymentMethods(api)

  if (!customer) {
    return null
  }

  return (
    <div className="flex flex-col gap-y-8">
      <h3 className="text-2xl">Settings</h3>
      <Well className="dark:bg-polar-900 flex flex-col gap-y-6 bg-gray-50">
        <WellHeader className="flex-row items-start justify-between">
          <div className="flex flex-col gap-y-2">
            <h3 className="text-xl">Payment Methods</h3>
            <p className="dark:text-polar-500 text-gray-500">
              Methods used for subscriptions & one-time purchases
            </p>
          </div>
          <Button onClick={showAddPaymentMethodModal}>
            Add Payment Method
          </Button>
        </WellHeader>
        <Separator className="dark:bg-polar-700" />
        <WellContent className="gap-y-4">
          {paymentMethods?.items.map((pm) => (
            <PaymentMethod key={pm.id} paymentMethod={pm} api={api} />
          ))}
        </WellContent>
      </Well>
      <Well className="dark:bg-polar-900 flex flex-col gap-y-6 bg-gray-50">
        <WellHeader className="flex-row items-center justify-between">
          <div className="flex flex-col gap-y-2">
            <h3 className="text-xl">Billing Details</h3>
            <p className="dark:text-polar-500 text-gray-500">
              Update your billing details
            </p>
          </div>
        </WellHeader>
        <Separator className="dark:bg-polar-700" />
        <WellContent>
          <EditBillingDetails
            api={api}
            customer={customer}
            onSuccess={() => {
              revalidate(`customer_portal`)
            }}
          />
        </WellContent>
      </Well>

      <Modal
        isShown={isAddPaymentMethodModalOpen}
        hide={hideAddPaymentMethodModal}
        modalContent={
          <AddPaymentMethodModal
            api={api}
            onPaymentMethodAdded={() => {
              revalidate(`customer_portal`)
              hideAddPaymentMethodModal()
            }}
            hide={hideAddPaymentMethodModal}
          />
        }
      />
    </div>
  )
}
