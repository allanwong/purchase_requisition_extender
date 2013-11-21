# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright 2013 AllanWong <seywong@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
# from datetime import datetime
# from dateutil.relativedelta import relativedelta
# import time
from openerp import netsvc

from openerp.osv import fields,osv
from openerp.tools.translate import _
# import openerp.addons.decimal_precision as dp


class purchase_requisition(osv.osv):
    _inherit = ['purchase.requisition']
    _name = "purchase.requisition"
    _description="Purchase Requisition Extender"

    def tender_in_progress(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        supplier_ids =[]
        purchase_order = self.pool.get('purchase.order')
        tender = self.pool.get('purchase.requisition').browse(cr, uid, ids, context=context)[0]
        supplierinfo_obj = self.pool.get('product.supplierinfo')
        requisition_id = self.browse(cr, uid, ids, context=context)[0].id
        po = purchase_order.search(cr,uid,[('requisition_id','=',requisition_id)])
        if po:return self.write(cr, uid, ids, {'state':'in_progress'} ,context=context)
        for line in tender.line_ids:
            product_id = line.product_id.id
            sinfo = supplierinfo_obj.search(cr, uid,
                    [('product_id', '=', product_id)])
            suppliers = supplierinfo_obj.browse(cr, uid, sinfo, context=context)
            for supplier in suppliers:
                if supplier.name.id not in supplier_ids:supplier_ids.append(supplier.name.id)
        for supplier_id in supplier_ids:
            self.pool.get('purchase.requisition').make_purchase_order_auto(cr, uid, ids, supplier_id, context=context)
        return self.write(cr, uid, ids, {'state':'in_progress'} ,context=context)

    def make_purchase_order_auto(self, cr, uid, ids, partner_id, context=None):
        """
        Create New RFQ for Supplier
        """
        if context is None:
            context = {}
        assert partner_id, 'Supplier should be specified'
        purchase_order = self.pool.get('purchase.order')
        purchase_order_line = self.pool.get('purchase.order.line')
        res_partner = self.pool.get('res.partner')
        fiscal_position = self.pool.get('account.fiscal.position')
        supplier = res_partner.browse(cr, uid, partner_id, context=context)
        supplier_pricelist = supplier.property_product_pricelist_purchase or False
        supplierinfo_obj = self.pool.get('product.supplierinfo')
        res = {}
        for requisition in self.browse(cr, uid, ids, context=context):
            if supplier.id in filter(lambda x: x, [rfq.state <> 'cancel' and rfq.partner_id.id or None for rfq in requisition.purchase_ids]):
                raise osv.except_osv(_('Warning!'), _('You have already one %s purchase order for this partner, you must cancel this purchase order to create a new quotation.') % rfq.state)
            location_id = requisition.warehouse_id.lot_input_id.id
            purchase_id = purchase_order.create(cr, uid, {
                        'origin': requisition.name,
                        'partner_id': supplier.id,
                        'pricelist_id': supplier_pricelist.id,
                        'location_id': location_id,
                        'company_id': requisition.company_id.id,
                        'fiscal_position': supplier.property_account_position and supplier.property_account_position.id or False,
                        'requisition_id':requisition.id,
                        'notes':requisition.description,
                        'warehouse_id':requisition.warehouse_id.id ,
            })
            res[requisition.id] = purchase_id
            for line in requisition.line_ids:
                product = line.product_id
                sinfo = supplierinfo_obj.search(cr, uid,['&',('product_id', '=', product.id),('name','=',partner_id)])
                if not sinfo : continue
                seller_price, qty, default_uom_po_id, date_planned = self._seller_details(cr, uid, line, supplier, context=context)
                taxes_ids = product.supplier_taxes_id
                taxes = fiscal_position.map_tax(cr, uid, supplier.property_account_position, taxes_ids)
                purchase_order_line.create(cr, uid, {
                    'order_id': purchase_id,
                    'name': product.partner_ref,
                    'product_qty': qty,
                    'product_id': product.id,
                    'product_uom': default_uom_po_id,
                    'price_unit': seller_price,
                    'date_planned': date_planned,
                    'taxes_id': [(6, 0, taxes)],
                }, context=context)
                
        return res


purchase_requisition()
# super(purchase_requisition, self)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
