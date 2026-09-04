// POS System JavaScript Engine
let cart = [];
let currentCategory = 'all';
// Guards against double submission from a rapid double-click or repeated F9.
let isSubmitting = false;

/** Escapes text before it is interpolated into an innerHTML string. */
function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

document.addEventListener('DOMContentLoaded', () => {
  setupProductCards();
  setupCategoryFilters();
  setupSearch();
  setupPaymentControls();
  setupKeyboardShortcuts();
  renderCart();
});

function setupKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    if (e.key === 'F9') {
      const el = document.activeElement;
      const inField = el && (
        ['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName) || el.isContentEditable
      );
      if (inField) return;
      e.preventDefault();
      const submitBtn = document.getElementById('submitOrderBtn');
      if (submitBtn && !submitBtn.disabled) {
        submitOrder();
      }
      return;
    }
    if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
      e.preventDefault();
      const searchInput = document.getElementById('posProductSearch');
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
      return;
    }
    if (e.key === 'Escape') {
      const modal = document.getElementById('orderSuccessModal');
      if (modal) {
        e.preventDefault();
        closeSuccessModal();
        return;
      }
      if (document.activeElement?.id === 'posProductSearch') {
        document.activeElement.blur();
      }
    }
  });
}

function setupProductCards() {
  document.querySelectorAll('.pos-item-card').forEach(card => {
    card.addEventListener('click', () => {
      addToCart(card);
    });
  });
}

function addToCart(itemOrId, name, price, sizeWeight, maxStock) {
  let productId, prodName, prodPrice, prodSizeWeight, prodMaxStock;

  if (typeof itemOrId === 'object' && itemOrId !== null) {
    const el = itemOrId;
    productId = parseInt(el.getAttribute('data-id'), 10);
    prodName = el.getAttribute('data-name');
    prodPrice = parseFloat(el.getAttribute('data-price')) || 0;
    prodSizeWeight = el.getAttribute('data-size') || '';
    const stockAttr = el.getAttribute('data-stock');
    prodMaxStock = stockAttr !== '' && stockAttr !== null ? parseInt(stockAttr, 10) : null;
  } else {
    productId = parseInt(itemOrId, 10);
    prodName = name;
    prodPrice = parseFloat(price) || 0;
    prodSizeWeight = sizeWeight || '';
    prodMaxStock = maxStock !== undefined ? maxStock : null;
  }

  if (!Number.isFinite(productId)) return;

  const existing = cart.find(item => item.product_id === productId);
  const alreadyInCart = existing ? existing.quantity : 0;

  // Respect the product's available stock; the server enforces this too, but
  // blocking it here avoids a wasted round-trip and a confusing rejection.
  if (prodMaxStock !== null && Number.isFinite(prodMaxStock) && alreadyInCart + 1 > prodMaxStock) {
    showToast(`Only ${prodMaxStock} unit(s) of ${prodName} available in stock`, 'warning');
    return;
  }

  if (existing) {
    existing.quantity += 1;
  } else {
    cart.push({
      product_id: productId,
      name: prodName,
      price: prodPrice,
      size_weight: prodSizeWeight,
      quantity: 1,
      max_stock: prodMaxStock
    });
  }
  renderCart();
  flashItemAdded(productId);
}

function updateQuantity(productId, delta) {
  const item = cart.find(item => item.product_id === productId);
  if (!item) return;

  const next = item.quantity + delta;
  if (next <= 0) {
    removeFromCart(productId);
    return;
  }
  if (item.max_stock !== null && Number.isFinite(item.max_stock) && next > item.max_stock) {
    showToast(`Only ${item.max_stock} unit(s) of ${item.name} available in stock`, 'warning');
    return;
  }
  item.quantity = next;
  renderCart();
}

function removeFromCart(productId) {
  cart = cart.filter(item => item.product_id !== productId);
  renderCart();
}

async function clearCart() {
  const nameInput = document.getElementById('customerNameInput');
  const phoneInput = document.getElementById('customerPhoneInput');
  const notesInput = document.getElementById('orderNotesInput');

  const hasCustomerInfo = (nameInput?.value.trim() || '') !== '' ||
                          (phoneInput?.value.trim() || '') !== '' ||
                          (notesInput?.value.trim() || '') !== '';

  if (cart.length === 0 && !hasCustomerInfo) {
    showToast("Cart is already empty", "info");
    return;
  }

  const confirmed = await showCustomConfirm(
    "Clear Current Order?",
    "Are you sure you want to clear all cart items and customer details?",
    "Yes, Clear Order",
    "Cancel",
    "warning",
    true
  );
  if (confirmed) {
    cart = [];

    if (nameInput) nameInput.value = '';
    if (phoneInput) phoneInput.value = '';
    if (notesInput) notesInput.value = '';

    const paymentSelect = document.getElementById('paymentMethodSelect');
    if (paymentSelect) paymentSelect.value = 'cash';

    const paidRadio = document.querySelector('input[name="payment_status_type"][value="paid"]');
    if (paidRadio) {
      paidRadio.checked = true;
    }

    renderCart();
    showToast("Order cart cleared", "info");
  }
}

function renderCart() {
  const cartContainer = document.getElementById('cartItemsContainer');
  const cartCountElem = document.getElementById('cartItemCount');
  const subtotalElem = document.getElementById('subtotalDisplay');
  const grandTotalElem = document.getElementById('grandTotalDisplay');
  const paidInput = document.getElementById('paidAmountInput');
  const pendingElem = document.getElementById('pendingAmountDisplay');
  const submitBtn = document.getElementById('submitOrderBtn');

  if (cart.length === 0) {
    cartContainer.innerHTML = `
      <div style="text-align: center; color: var(--text-muted); padding: 32px 10px; margin: auto;">
        <div style="width: 52px; height: 52px; border-radius: 50%; background: var(--bg-card); border: 1px dashed var(--border-color); display: flex; align-items: center; justify-content: center; margin: 0 auto 10px auto; font-size: 1.5rem; box-shadow: 0 2px 6px rgba(0,0,0,0.03);">
          🎂
        </div>
        <p style="font-weight: 700; font-size: 0.92rem; color: var(--text-main); margin-bottom: 3px;">Cart is empty</p>
        <p style="font-size: 0.78rem; color: var(--text-muted); max-width: 200px; margin: 0 auto; line-height: 1.4;">Click any cake from the catalog to add to order</p>
      </div>
    `;
    cartCountElem.innerText = '0 items';
    subtotalElem.innerText = '₹0.00';
    grandTotalElem.innerText = '₹0.00';
    pendingElem.innerText = '₹0.00';
    paidInput.value = 0;
    submitBtn.disabled = true;
    recalcPayment(0);
    return;
  }

  submitBtn.disabled = false;
  let totalItems = 0;
  let subtotal = 0;

  let html = '';
  cart.forEach(item => {
    const itemTotal = item.price * item.quantity;
    totalItems += item.quantity;
    subtotal += itemTotal;

    html += `
      <div class="pos-cart-item">
        <div style="flex: 1; min-width: 0; padding-right: 8px;">
          <div style="font-weight: 700; font-size: 0.88rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text-main); margin-bottom: 2px;" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</div>
          <div style="display: flex; align-items: center; gap: 6px; font-size: 0.75rem; color: var(--text-muted);">
            <span>₹${item.price.toFixed(2)}</span>
            ${item.size_weight ? `<span class="pos-item-size-badge" style="padding: 0 5px; font-size: 0.68rem;">${escapeHtml(item.size_weight)}</span>` : ''}
          </div>
        </div>
        
        <div style="display: flex; align-items: center; gap: 8px;">
          <div class="pos-stepper">
            <button type="button" class="pos-stepper-btn" onclick="updateQuantity(${item.product_id}, -1)" title="Decrease quantity">−</button>
            <span class="pos-stepper-qty">${item.quantity}</span>
            <button type="button" class="pos-stepper-btn" onclick="updateQuantity(${item.product_id}, 1)" title="Increase quantity">+</button>
          </div>
          
          <div style="font-weight: 800; font-size: 0.92rem; min-width: 60px; text-align: right; color: var(--cherry); font-family: var(--font-heading);">
            ₹${itemTotal.toFixed(2)}
          </div>
          
          <button type="button" style="color: var(--text-muted); background: transparent; border: none; padding: 4px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s ease;" onmouseover="this.style.color='var(--danger)'; this.style.background='var(--danger-light)';" onmouseout="this.style.color='var(--text-muted)'; this.style.background='transparent';" onclick="removeFromCart(${item.product_id})" title="Remove item">
            <svg style="width: 14px; height: 14px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
          </button>
        </div>
      </div>
    `;
  });

  cartContainer.innerHTML = html;
  cartCountElem.innerText = `${totalItems} items`;

  const grandTotal = Math.max(0, subtotal);

  subtotalElem.innerText = `₹${subtotal.toFixed(2)}`;
  grandTotalElem.innerText = `₹${grandTotal.toFixed(2)}`;

  // Payment Calculation
  recalcPayment(grandTotal);
}

function recalcPayment(grandTotal) {
  if (grandTotal === undefined) {
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    grandTotal = Math.max(0, subtotal);
  }

  const paymentStatusType = document.querySelector('input[name="payment_status_type"]:checked').value;
  const paidInput = document.getElementById('paidAmountInput');
  const pendingElem = document.getElementById('pendingAmountDisplay');
  const paymentStatusBadge = document.getElementById('orderPaymentBadge');

  if (paymentStatusType === 'paid') {
    paidInput.value = grandTotal.toFixed(2);
    paidInput.readOnly = true;
    pendingElem.innerText = '₹0.00';
    paymentStatusBadge.innerHTML = '<span class="badge badge-paid">Fully Paid</span>';
  } else if (paymentStatusType === 'pending') {
    paidInput.value = '0.00';
    paidInput.readOnly = true;
    pendingElem.innerText = `₹${grandTotal.toFixed(2)}`;
    paymentStatusBadge.innerHTML = '<span class="badge badge-pending">Pending / Udhaar</span>';
  } else if (paymentStatusType === 'partial') {
    paidInput.readOnly = false;
    let paidVal = parseFloat(paidInput.value) || 0;
    if (paidVal > grandTotal) {
      paidVal = grandTotal;
      paidInput.value = grandTotal.toFixed(2);
    }
    const pendingVal = Math.max(0, grandTotal - paidVal);
    pendingElem.innerText = `₹${pendingVal.toFixed(2)}`;
    paymentStatusBadge.innerHTML = '<span class="badge badge-partially_paid">Partially Paid</span>';
  }
}

function setupPaymentControls() {
  document.querySelectorAll('input[name="payment_status_type"]').forEach(radio => {
    radio.addEventListener('change', () => recalcPayment());
  });

  const paidInput = document.getElementById('paidAmountInput');
  if (paidInput) {
    paidInput.addEventListener('input', () => recalcPayment());
  }
}

function setupCategoryFilters() {
  document.querySelectorAll('.pos-cat-pill').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.pos-cat-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentCategory = btn.getAttribute('data-cat-id');
      filterProducts();
    });
  });
}

function setupSearch() {
  const searchInput = document.getElementById('posProductSearch');
  if (searchInput) {
    searchInput.addEventListener('input', () => filterProducts());
  }
}

function filterProducts() {
  const query = (document.getElementById('posProductSearch').value || '').toLowerCase().trim();
  const cards = document.querySelectorAll('.pos-item-card');

  cards.forEach(card => {
    const name = card.getAttribute('data-name').toLowerCase();
    const sku = (card.getAttribute('data-sku') || '').toLowerCase();
    const catId = card.getAttribute('data-cat-id');

    const matchesCat = (currentCategory === 'all' || catId === currentCategory);
    const matchesSearch = (!query || name.includes(query) || sku.includes(query));

    if (matchesCat && matchesSearch) {
      card.style.display = 'flex';
    } else {
      card.style.display = 'none';
    }
  });
}

function flashItemAdded(productId) {
  const card = document.querySelector(`.pos-item-card[data-id="${productId}"]`);
  if (card) {
    card.style.transform = 'scale(0.96)';
    card.style.borderColor = 'var(--success)';
    setTimeout(() => {
      card.style.transform = '';
      card.style.borderColor = '';
    }, 180);
  }
}

async function submitOrder() {
  if (isSubmitting) return;

  if (cart.length === 0) {
    showCustomAlert("Cart is Empty", "Please select and add at least one item to the cart before submitting.", "warning");
    return;
  }

  const customerName = document.getElementById('customerNameInput').value.trim() || 'Walk-in Customer';
  const customerPhone = document.getElementById('customerPhoneInput').value.trim();
  const paymentMethod = document.getElementById('paymentMethodSelect').value;
  const paidAmount = parseFloat(document.getElementById('paidAmountInput').value) || 0;
  const notes = document.getElementById('orderNotesInput').value.trim();

  const paymentStatusType = document.querySelector('input[name="payment_status_type"]:checked').value;
  const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  const grandTotal = Math.max(0, subtotal);

  if (paymentStatusType === 'partial') {
    if (paidAmount <= 0) {
      showCustomAlert("Invalid Partial Payment Amount", "For Partial Payment, the Amount Paid must be greater than ₹0.00. If no payment is collected upfront, please select 'Udhaar'.", "warning");
      return;
    }
    if (paidAmount >= grandTotal && grandTotal > 0) {
      showCustomAlert("Invalid Partial Payment Amount", `For Partial Payment, the Amount Paid must be less than the Grand Total (₹${grandTotal.toFixed(2)}). If full payment is collected, please select 'Full Paid'.`, "warning");
      return;
    }
  }

    const payload = {
      customer_name: customerName,
      customer_phone: customerPhone,
      discount: 0,
      payment_method: paymentMethod,
      payment_status_type: paymentStatusType,
      paid_amount: paidAmount,
      notes: notes,
      items: cart.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity
      }))
    };

    const submitBtn = document.getElementById('submitOrderBtn');
    isSubmitting = true;
    submitBtn.disabled = true;
    submitBtn.innerText = 'Processing Order...';

    try {
      const result = await apiFetch('/orders/api/create', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (result.success) {
        // Prompt modal with receipt options
        showOrderSuccessModal(result.order_number, result.receipt_url);
        cart = [];
        document.getElementById('customerNameInput').value = '';
        document.getElementById('customerPhoneInput').value = '';
        document.getElementById('orderNotesInput').value = '';
        renderCart();
      showToast("Order " + result.order_number + " completed!", "success");
    } else {
      showCustomAlert("Order Failed", result.error || "Unable to complete order. Please check inventory levels.", "error");
    }
  } catch (err) {
    showCustomAlert("Order Failed", err.message || "Failed to communicate with the server.", "error");
  } finally {
    isSubmitting = false;
    submitBtn.disabled = cart.length === 0;
    submitBtn.innerHTML = `
      <svg style="width: 20px; height: 20px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
      </svg>
      Complete Order (F9)
    `;
  }
}

function showOrderSuccessModal(orderNumber, receiptUrl) {
  const modalHtml = `
    <div class="modal-backdrop" id="orderSuccessModal">
      <div class="modal-content" style="text-align: center; max-width: 440px;">
        <div class="modal-body" style="padding: 30px;">
          <div style="width: 64px; height: 64px; border-radius: 50%; background: var(--success-light); color: var(--success); display: flex; align-items: center; justify-content: center; margin: 0 auto 16px;">
            <svg style="width: 36px; height: 36px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
          </div>
          <h3 style="margin-bottom: 8px;">Order Placed!</h3>
          <p style="color: var(--text-muted); font-size: 0.95rem; margin-bottom: 20px;">Order <strong>${escapeHtml(orderNumber)}</strong> was recorded successfully.</p>
          <div style="display: flex; flex-direction: column; gap: 10px;">
            <a href="${encodeURI(receiptUrl)}" target="_blank" rel="noopener" class="btn btn-primary btn-lg">
              <svg style="width: 20px; height: 20px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
              Print Receipt / Invoice
            </a>
            <button type="button" class="btn btn-secondary" onclick="closeSuccessModal()">Start New Order</button>
          </div>
        </div>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function closeSuccessModal() {
  const modal = document.getElementById('orderSuccessModal');
  if (modal) modal.remove();
}
