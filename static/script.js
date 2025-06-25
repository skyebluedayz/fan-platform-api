// ファイルアップロード機能
document.addEventListener('DOMContentLoaded', function() {
    // DOM要素の取得
    const uploadArea = document.getElementById('upload-area');
    const uploadBtn = document.getElementById('upload-btn');
    const fileInput = document.getElementById('file-input');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress');
    const statusText = document.getElementById('status');
    const fileList = document.getElementById('file-list');
    const uploadedFiles = document.getElementById('uploaded-files');
    const refreshBtn = document.getElementById('refresh-btn');

    // 初期化
    loadUploadedFiles();
    setupEventListeners();

    // イベントリスナーの設定
    function setupEventListeners() {
        // アップロードエリアのクリック
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // ドラッグ&ドロップ
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });
        
        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            const files = Array.from(e.dataTransfer.files);
            handleFiles(files);
        });
        
        // ボタンのクリック
        uploadBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });
        
        // ファイル選択
        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            handleFiles(files);
        });
        
        // 更新ボタン
        refreshBtn.addEventListener('click', loadUploadedFiles);
    }

    // ファイル処理
    function handleFiles(files) {
        if (files.length === 0) return;
        
        progressContainer.style.display = 'block';
        displaySelectedFiles(files);
        uploadFiles(files);
    }

    // 選択されたファイルの表示
    function displaySelectedFiles(files) {
        fileList.innerHTML = '';
        
        files.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.innerHTML = `
                <div class="file-info">
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${formatFileSize(file.size)}</span>
                </div>
                <div class="file-status uploading">⬆️ アップロード中...</div>
                <div class="file-progress">
                    <div class="progress-bar" style="width: 0%"></div>
                </div>
            `;
            fileList.appendChild(fileItem);
        });
    }

    // ファイルサイズのフォーマット
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // ファイルのアップロード
    async function uploadFiles(files) {
        let completed = 0;
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    updateFileStatus(i, 'success', '✅ 完了');
                } else {
                    updateFileStatus(i, 'error', '❌ エラー');
                }
            } catch (error) {
                updateFileStatus(i, 'error', '❌ エラー');
            }
            
            completed++;
            updateOverallProgress(completed, files.length);
        }
        
        setTimeout(() => {
            loadUploadedFiles();
            progressContainer.style.display = 'none';
        }, 2000);
    }

    // ファイルステータスの更新
    function updateFileStatus(index, status, text) {
        const fileItems = fileList.querySelectorAll('.file-item');
        if (fileItems[index]) {
            const statusElement = fileItems[index].querySelector('.file-status');
            const progressElement = fileItems[index].querySelector('.progress-bar');
            
            if (statusElement) {
                statusElement.textContent = text;
                statusElement.className = `file-status ${status}`;
            }
            
            if (progressElement && status === 'success') {
                progressElement.style.width = '100%';
            }
        }
    }

    // 全体の進行状況を更新
    function updateOverallProgress(completed, total) {
        const progress = (completed / total) * 100;
        progressBar.style.width = `${progress}%`;
        
        if (completed === total) {
            statusText.textContent = '✅ 全てのアップロードが完了しました';
        } else {
            statusText.textContent = `📤 アップロード中... (${completed}/${total})`;
        }
    }

    // 保存済みファイルの読み込み
    async function loadUploadedFiles() {
        try {
            const response = await fetch('/files');
            const files = await response.json();
            
            uploadedFiles.innerHTML = '';
            
            if (files.length === 0) {
                uploadedFiles.innerHTML = '<p style="text-align: center; color: #888; padding: 20px;">まだファイルがアップロードされていません</p>';
                return;
            }
            
            files.forEach(file => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                fileItem.innerHTML = `
                    <div class="file-info">
                        <span class="file-name">${file.name}</span>
                        <span class="file-size">${formatFileSize(file.size)}</span>
                    </div>
                    <div class="file-status success">✅ 保存済み</div>
                    <div class="file-actions">
                        <button class="btn-download" onclick="downloadFile('${file.name}')">📥 ダウンロード</button>
                        <button class="btn-delete" onclick="deleteFile('${file.name}')">🗑️ 削除</button>
                    </div>
                `;
                uploadedFiles.appendChild(fileItem);
            });
        } catch (error) {
            uploadedFiles.innerHTML = '<p style="text-align: center; color: #f00; padding: 20px;">ファイルの読み込みに失敗しました</p>';
        }
    }
});

// グローバル関数（HTML から呼び出される）
function downloadFile(filename) {
    window.open(`/download/${encodeURIComponent(filename)}`, '_blank');
}

async function deleteFile(filename) {
    if (!confirm(`"${filename}" を削除しますか？`)) {
        return;
    }
    
    try {
        const response = await fetch(`/delete/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // ページをリロードして更新
            window.location.reload();
        } else {
            const errorData = await response.json();
            alert(`削除に失敗しました: ${errorData.error}`);
        }
    } catch (error) {
        alert('削除中にエラーが発生しました');
    }
}
