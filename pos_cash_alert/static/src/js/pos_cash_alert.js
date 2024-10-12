odoo.define('pos_cash_alert.pos_cash_alert', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');

    const PosCashAlertPaymentScreen = (PaymentScreen) => class extends PaymentScreen {
        async _finalizeValidation() {
            await super._finalizeValidation();

            const maxCashLimit = this.env.pos.config.max_cash_limit;
            const currentCash = this.env.pos.get_order().get_payment_total('cash');

            if (currentCash >= maxCashLimit && maxCashLimit > 0) {
                this.showPopup('ConfirmPopup', {
                    title: 'Límite de efectivo alcanzado',
                    body: `Ha alcanzado su límite de efectivo máximo por la cantidad de ${currentCash}. Favor de hacer el retiro correspondiente.`,
                });
            }
        }
    };

    Registries.Component.extend(PaymentScreen, PosCashAlertPaymentScreen);
});
