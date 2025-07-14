// Salary Cap Live Data Integration
// Connects the HTML module to live Spotrac JSON data
// Auto-refreshes every 5 minutes

class SalaryCapDataManager {
    constructor() {
        this.dataUrl = 'data/salary_cap_data.json';
        this.lastUpdate = null;
        this.currentData = null;
        this.refreshInterval = 5 * 60 * 1000; // 5 minutes
        this.autoRefreshTimer = null;
    }

    // Load live data from JSON file
    async loadLiveData() {
        try {
            console.log('🔄 Loading live salary cap data...');
            
            const response = await fetch(this.dataUrl + '?t=' + Date.now()); // Cache buster
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            console.log('✅ Live data loaded successfully:', data);
            
            this.currentData = data;
            this.lastUpdate = new Date(data.last_updated);
            
            return data;
            
        } catch (error) {
            console.error('❌ Error loading live data:', error);
            
            // Return fallback data if live data fails
            return this.getFallbackData();
        }
    }

    // Update all UI elements with live data
    async updateUI() {
        const data = await this.loadLiveData();
        
        if (!data) {
            console.error('No data available to update UI');
            return;
        }

        try {
            // Update salary cap overview
            this.updateCapOverview(data.salary_cap);
            
            // Update contract list
            this.updateContractList(data.top_contracts);
            
            // Update last refresh time
            this.updateLastRefreshTime(data.last_updated);
            
            // Update cap status
            this.updateCapStatus(data.salary_cap);
            
            console.log('✅ UI updated with live data');
            
        } catch (error) {
            console.error('❌ Error updating UI:', error);
        }
    }

    // Update salary cap overview metrics
    updateCapOverview(capData) {
        // Update total cap
        const totalCapElement = document.getElementById('totalCap');
        if (totalCapElement) {
            totalCapElement.textContent = this.formatCurrency(capData.total_cap);
        }

        // Update used cap
        const usedCapElement = document.getElementById('usedCap');
        if (usedCapElement) {
            usedCapElement.textContent = this.formatCurrency(capData.used_cap);
        }

        // Update available cap
        const availableCapElement = document.getElementById('availableCap');
        if (availableCapElement) {
            availableCapElement.textContent = this.formatCurrency(capData.available_cap);
        }

        // Update dead money
        const deadMoneyElement = document.getElementById('deadMoney');
        if (deadMoneyElement) {
            deadMoneyElement.textContent = this.formatCurrency(capData.dead_money);
        }

        // Update percentage indicators
        const usedCapChange = document.getElementById('usedCapChange');
        if (usedCapChange) {
            usedCapChange.textContent = `${capData.cap_percentage}% of total`;
        }

        console.log('📊 Cap overview updated');
    }

    // Update cap status indicator
    updateCapStatus(capData) {
        const statusElement = document.getElementById('capStatus');
        if (!statusElement) return;

        const percentage = capData.cap_percentage;
        
        if (percentage < 85) {
            statusElement.textContent = 'Healthy';
            statusElement.className = 'cap-status healthy';
            statusElement.style.background = 'var(--cap-healthy)';
        } else if (percentage < 95) {
            statusElement.textContent = 'Warning';
            statusElement.className = 'cap-status warning';
            statusElement.style.background = 'var(--cap-warning)';
        } else {
            statusElement.textContent = 'Critical';
            statusElement.className = 'cap-status critical';
            statusElement.style.background = 'var(--cap-danger)';
        }

        console.log(`🚦 Cap status updated: ${statusElement.textContent} (${percentage}%)`);
    }

    // Update contract list with live player data
    updateContractList(contracts) {
        const contractList = document.getElementById('contractList');
        if (!contractList) return;

        // Clear existing contracts
        contractList.innerHTML = '';

        // Add live contract data
        contracts.forEach(contract => {
            const contractItem = this.createContractItem(contract);
            contractList.appendChild(contractItem);
        });

        console.log(`📝 Contract list updated with ${contracts.length} contracts`);
    }

    // Create individual contract item HTML
    createContractItem(contract) {
        const contractDiv = document.createElement('div');
        contractDiv.className = 'contract-item';
        contractDiv.onclick = () => this.showContractDetails(contract);

        contractDiv.innerHTML = `
            <div class="contract-player">
                <span class="player-name">${contract.player_name}</span>
                <span class="player-position">${contract.position}</span>
            </div>
            <div class="contract-details">
                <div class="detail-item">Cap Hit: <span class="detail-value">${this.formatCurrency(contract.cap_hit_2025)}</span></div>
                <div class="detail-item">Guaranteed: <span class="detail-value">${this.formatCurrency(contract.guaranteed)}</span></div>
                <div class="detail-item">Years Left: <span class="detail-value">${contract.years_remaining}</span></div>
            </div>
        `;

        return contractDiv;
    }

    // Show detailed contract information
    showContractDetails(contract) {
        const details = `
            Player: ${contract.player_name} (${contract.position})
            2025 Cap Hit: ${this.formatCurrency(contract.cap_hit_2025)}
            Total Value: ${this.formatCurrency(contract.total_value)}
            Guaranteed: ${this.formatCurrency(contract.guaranteed)}
            Years Remaining: ${contract.years_remaining}
            Restructure Potential: ${contract.restructure_potential ? 'Yes' : 'No'}
        `;
        
        alert(details);
    }

    // Update last refresh time display
    updateLastRefreshTime(lastUpdated) {
        const timeElement = document.getElementById('lastUpdateTime');
        if (!timeElement) return;

        const updateTime = new Date(lastUpdated);
        const timeString = updateTime.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        });

        timeElement.textContent = timeString;
        console.log(`⏰ Last update time: ${timeString}`);
    }

    // Format currency values
    formatCurrency(amount) {
        if (amount === 0) return '$0';
        
        const millions = amount / 1000000;
        if (millions >= 1) {
            return `$${millions.toFixed(1)}M`;
        } else {
            const thousands = amount / 1000;
            return `$${thousands.toFixed(0)}K`;
        }
    }

    // Start auto-refresh
    startAutoRefresh() {
        console.log('🔄 Starting auto-refresh every 5 minutes...');
        
        // Initial load
        this.updateUI();
        
        // Set up interval
        this.autoRefreshTimer = setInterval(() => {
            console.log('⏰ Auto-refresh triggered');
            this.updateUI();
        }, this.refreshInterval);
    }

    // Stop auto-refresh
    stopAutoRefresh() {
        if (this.autoRefreshTimer) {
            clearInterval(this.autoRefreshTimer);
            this.autoRefreshTimer = null;
            console.log('⏹️ Auto-refresh stopped');
        }
    }

    // Manually refresh data
    async manualRefresh() {
        console.log('🔄 Manual refresh triggered');
        
        // Show loading state
        document.body.classList.add('loading');
        
        try {
            await this.updateUI();
        } finally {
            // Remove loading state
            setTimeout(() => {
                document.body.classList.remove('loading');
            }, 1000);
        }
    }

    // Fallback data if live data fails
    getFallbackData() {
        return {
            team: 'Philadelphia Eagles',
            last_updated: new Date().toISOString(),
            salary_cap: {
                total_cap: 255000000,
                used_cap: 250800000,
                available_cap: 4200000,
                dead_money: 8500000,
                cap_percentage: 98.4
            },
            top_contracts: [
                {
                    player_name: 'Jalen Hurts',
                    position: 'QB',
                    cap_hit_2025: 13000000,
                    total_value: 255000000,
                    guaranteed: 110000000,
                    years_remaining: 4,
                    restructure_potential: true
                },
                {
                    player_name: 'A.J. Brown',
                    position: 'WR',
                    cap_hit_2025: 10200000,
                    total_value: 100000000,
                    guaranteed: 57000000,
                    years_remaining: 3,
                    restructure_potential: true
                },
                {
                    player_name: 'Lane Johnson',
                    position: 'OT',
                    cap_hit_2025: 8700000,
                    total_value: 72000000,
                    guaranteed: 0,
                    years_remaining: 1,
                    restructure_potential: true
                }
            ]
        };
    }

    // Get current data
    getCurrentData() {
        return this.currentData;
    }

    // Check if data is fresh (less than 10 minutes old)
    isDataFresh() {
        if (!this.lastUpdate) return false;
        
        const now = new Date();
        const diffMinutes = (now - this.lastUpdate) / (1000 * 60);
        
        return diffMinutes < 10;
    }
}

// Global instance
let salaryCapManager = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing Salary Cap Data Manager...');
    
    salaryCapManager = new SalaryCapDataManager();
    salaryCapManager.startAutoRefresh();
    
    // Expose refresh function globally
    window.refreshData = function() {
        if (salaryCapManager) {
            salaryCapManager.manualRefresh();
        }
    };
    
    // Expose manual data loading
    window.loadSalaryCapData = function() {
        if (salaryCapManager) {
            return salaryCapManager.updateUI();
        }
    };
    
    console.log('✅ Salary Cap Data Manager initialized');
});

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SalaryCapDataManager;
}
