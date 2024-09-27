document.getElementById('create-orchestrator-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData(this);
    const orchestratorData = Object.fromEntries(formData.entries());

    try {
        const response = await fetch('/orchestrators', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(orchestratorData),
        });

        if (response.ok) {
            this.reset();
            document.body.dispatchEvent(new Event('orchestratorCreated'));
        } else {
            console.error('Failed to create orchestrator');
        }
    } catch (error) {
        console.error('Error:', error);
    }
});
