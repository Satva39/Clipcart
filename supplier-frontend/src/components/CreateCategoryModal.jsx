import { useState } from "react";

export default function CreateCategoryModal({
    onClose,
    onCreated,
}) {
    const [name, setName] =
        useState("");

    const [loading, setLoading] =
        useState(false);

    const [error, setError] =
        useState("");

    async function handleSubmit(event) {
        event.preventDefault();

        if (!name.trim()) {
            setError(
                "Category name is required."
            );
            return;
        }

        try {
            setLoading(true);
            setError("");

            /*
             * Connect this to the category
             * creation endpoint when the
             * backend route is added.
             */
            onCreated({
                name: name.trim(),
            });

            onClose();
        } catch (err) {
            console.error(
                "Failed to create category:",
                err
            );

            setError(
                "Unable to create category."
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="creation-modal-backdrop">

            <div className="creation-modal">

                <h2>
                    Create Category
                </h2>

                <p>
                    Add a new category for
                    your products.
                </p>

                {error && (
                    <div className="creation-modal-error">
                        {error}
                    </div>
                )}

                <form
                    onSubmit={handleSubmit}
                >

                    <input
                        value={name}
                        onChange={(event) =>
                            setName(
                                event.target
                                    .value
                            )
                        }
                        placeholder="e.g. Smartphones"
                        autoFocus
                    />

                    <div className="creation-modal-actions">

                        <button
                            type="button"
                            onClick={onClose}
                        >
                            Cancel
                        </button>

                        <button
                            type="submit"
                            disabled={loading}
                        >
                            {loading
                                ? "Creating..."
                                : "Create Category"}
                        </button>

                    </div>

                </form>

            </div>

        </div>
    );
}