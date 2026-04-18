<script setup>
import { AgGridVue } from 'ag-grid-vue3'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'

const props = defineProps({
  rowData: { type: Array, default: () => [] },
  columnDefs: { type: Array, default: () => [] },
  readOnly: { type: Boolean, default: false }
})

const emit = defineEmits(['save', 'cellValueChanged'])

const gridOptions = {
  defaultColDef: {
    sortable: true,
    filter: true,
    resizable: true,
    editable: !props.readOnly
  },
  onCellValueChanged: (params) => {
    emit('cellValueChanged', params.data)
  }
}

const onGridReady = (params) => {
  params.api.sizeColumnsToFit()
}
</script>

<template>
  <div class="xlsx-viewer">
    <div class="grid-toolbar glass-panel">
      <button @click="emit('save')" class="save-excel-btn">Save Changes</button>
    </div>
    <div class="grid-viewport ag-theme-alpine-dark">
      <ag-grid-vue
        class="ag-theme-alpine-dark"
        style="width: 100%; height: 100%;"
        :columnDefs="columnDefs"
        :rowData="rowData"
        :gridOptions="gridOptions"
        @grid-ready="onGridReady"
      >
      </ag-grid-vue>
    </div>
  </div>
</template>

<style scoped>
.xlsx-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #181d1f;
}

.grid-toolbar {
  padding: 12px 24px;
  background: #1c2224;
  border-bottom: 1px solid #2d3436;
  display: flex;
  justify-content: flex-end;
}

.save-excel-btn {
  background: var(--mango-primary);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}
.save-excel-btn:hover { background: var(--mango-glow); }

.grid-viewport {
  flex: 1;
}

:deep(.ag-theme-alpine-dark) {
  --ag-background-color: #181d1f;
  --ag-header-background-color: #1c2224;
  --ag-odd-row-background-color: #1a2022;
  --ag-border-color: #2d3436;
  --ag-font-size: 13px;
  --ag-font-family: 'Inter', sans-serif;
}
</style>
