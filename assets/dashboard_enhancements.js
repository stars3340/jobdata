// 智能招聘数据分析平台 - 前端增强脚本
// 包含动画效果、交互优化、用户体验提升等功能

console.log('🚀 加载仪表盘增强功能...');

window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        // 数字动画计数器
        animate_counter: function(target_value, element_id) {
            const element = document.getElementById(element_id);
            if (!element) return target_value;
            
            const start_value = 0;
            const duration = 2000; // 2秒动画
            const start_time = performance.now();
            
            function updateCounter(current_time) {
                const elapsed = current_time - start_time;
                const progress = Math.min(elapsed / duration, 1);
                
                // 使用easeOutCubic缓动函数
                const eased_progress = 1 - Math.pow(1 - progress, 3);
                const current_value = Math.floor(start_value + (target_value - start_value) * eased_progress);
                
                element.textContent = current_value.toLocaleString();
                
                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                }
            }
            
            requestAnimationFrame(updateCounter);
            return target_value;
        },
        
        // 平滑滚动到元素
        smooth_scroll_to: function(element_id) {
            const element = document.getElementById(element_id);
            if (element) {
                element.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
            return window.dash_clientside.no_update;
        },
        
        // 主题切换动画
        switch_theme: function(theme) {
            document.documentElement.style.setProperty('--transition-duration', '0.3s');
            
            setTimeout(() => {
                document.documentElement.style.removeProperty('--transition-duration');
            }, 300);
            
            return theme;
        }
    }
});

// 等待DOM加载完成
document.addEventListener('DOMContentLoaded', function() {
    console.log('✨ 初始化增强功能');
    initializeEnhancements();
});

function initializeEnhancements() {
    // 初始化各种功能
    setupAnimations();
    setupTooltips();
    setupKeyboardShortcuts();
    setupPerformanceMonitoring();
    setupNotifications();
}

// 动画效果设置
function setupAnimations() {
    // 为卡片添加悬停效果
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
            this.style.transition = 'all 0.3s ease';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

// 工具提示设置
function setupTooltips() {
    // 自定义工具提示实现
    const tooltip = document.createElement('div');
    tooltip.id = 'custom-tooltip';
    tooltip.style.cssText = `
        position: absolute;
        background: rgba(35, 41, 70, 0.95);
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        z-index: 10000;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.2s;
    `;
    document.body.appendChild(tooltip);
}

// 键盘快捷键
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            const refreshBtn = document.getElementById('refresh-btn');
            if (refreshBtn) refreshBtn.click();
        }
    });
}

// 性能监控
function setupPerformanceMonitoring() {
    const startTime = performance.now();
    
    window.addEventListener('load', function() {
        const loadTime = performance.now() - startTime;
        console.log(`页面加载时间: ${loadTime.toFixed(2)}ms`);
    });
}

// 通知系统
function setupNotifications() {
    window.showNotification = function(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.innerHTML = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #118AB2;
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            z-index: 10000;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    };
}

console.log('✅ 增强功能加载完成'); 