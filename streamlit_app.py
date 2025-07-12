"""
TrackMyPDB - Streamlit Application
@author Anu Gamage

A comprehensive bioinformatics pipeline for extracting heteroatoms from protein structures
and finding molecularly similar compounds using advanced fingerprint-based similarity analysis.

Licensed under MIT License - Open Source Project
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import sys
import base64
from datetime import datetime
from backend.agent_core import TrackMyPDBAgent
from backend.nl_interface import NaturalLanguageInterface

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Import backend modules
try:
    from backend.heteroatom_extractor import HeteroatomExtractor
    # Import RDKit first to ensure it's available
    import rdkit
    from backend.similarity_analyzer import SimilarityAnalyzer
except ImportError as e:
    # Only fall back to simplified version if RDKit specifically fails
    if 'rdkit' in str(e):
        from backend.similarity_analyzer_simple import MolecularSimilarityAnalyzer as SimilarityAnalyzer
        st.warning("⚠️ RDKit not available - using simplified molecular similarity")
    else:
        st.error(f"Error importing backend modules: {e}")
        st.stop()

# Page configuration
st.set_page_config(
    page_title="TrackMyPDB - AI-Powered Protein-Ligand Analysis",
    page_icon="🧬",
    layout="wide"
)

# Initialize components
@st.cache_resource
def initialize_agent():
    agent = TrackMyPDBAgent()
    return agent

if "agent" not in st.session_state:
    st.session_state.agent = initialize_agent()

if "nl_interface" not in st.session_state:
    st.session_state.nl_interface = NaturalLanguageInterface(st.session_state.agent)

def main():
    st.title("🧬 TrackMyPDB - AI-Powered Analysis")
    
    # Sidebar with analysis mode selection
    st.sidebar.title("Analysis Mode")
    mode = st.sidebar.selectbox(
        "Choose your interaction mode:",
        ["🤖 Natural Language", "📊 Traditional Interface"]
    )
    
    if mode == "🤖 Natural Language":
        st.session_state.nl_interface.render_chat_interface()
    else:
        render_traditional_interface()

def render_traditional_interface():
    """Render the traditional interface with advanced analysis options"""
    st.subheader("Traditional Analysis Interface")
    
    if 'heteroatom_results' not in st.session_state:
        st.session_state.heteroatom_results = None
    
    analysis_type = st.selectbox(
        "Analysis Type",
        ["🔍 Heteroatom Extraction", "🧪 Similarity Analysis", "📊 Complete Pipeline"]
    )
    
    if analysis_type == "🔍 Heteroatom Extraction":
        st.subheader("Heteroatom Extraction")
        
        uniprot_input = st.text_area(
            "UniProt IDs (one per line or comma-separated)",
            help="💡 AI Tip: Enter one or more UniProt IDs to analyze"
        )
        
        if st.button("🚀 Extract Heteroatoms"):
            if uniprot_input:
                uniprot_ids = [id.strip() for id in uniprot_input.replace(',', '\n').split('\n') if id.strip()]
                
                with st.spinner("🧬 Analyzing proteins..."):
                    results = st.session_state.agent.execute_action(
                        "extract_heteroatoms",
                        {"uniprot_ids": uniprot_ids}
                    )
                    
                if "error" in results:
                    st.error(f"Error: {results['error']}")
                else:
                    st.success("✅ Analysis complete!")
                    st.session_state.heteroatom_results = results["results"]
                    st.write(results["results"])
    
    elif analysis_type == "🧪 Similarity Analysis":
        st.subheader("Similarity Analysis")
        
        if st.session_state.heteroatom_results is None:
            st.warning("⚠️ Please run heteroatom extraction first")
            return
        
        # Advanced molecular analysis options
        with st.expander("🔬 Advanced Analysis Options", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                fp_type = st.selectbox(
                    "Fingerprint Type",
                    options=list(SimilarityAnalyzer.FINGERPRINT_TYPES.keys()),
                    help="""
                    - Morgan: Extended connectivity fingerprints (ECFP)
                    - MACCS: 166 predefined structural keys
                    - Topological: Atom pair fingerprints
                    - RDKit: RDKit's default fingerprints
                    - Pattern: Detailed atom pair patterns
                    """
                )
                
                similarity_metric = st.selectbox(
                    "Similarity Metric",
                    options=list(SimilarityAnalyzer.SIMILARITY_METRICS.keys()),
                    help="""
                    - Tanimoto: Standard similarity coefficient
                    - Dice: Emphasizes common features
                    - Cosine: Angular similarity between fingerprints
                    """
                )
            
            with col2:
                if fp_type == 'morgan':
                    radius = st.slider(
                        "Morgan Fingerprint Radius",
                        min_value=1,
                        max_value=4,
                        value=2,
                        help="Radius parameter for Morgan fingerprint generation"
                    )
                    n_bits = st.slider(
                        "Number of Bits",
                        min_value=512,
                        max_value=4096,
                        value=2048,
                        step=512,
                        help="Number of bits in fingerprint"
                    )
                else:
                    radius = 2
                    n_bits = 2048
        
        smiles_input = st.text_area(
            "SMILES String",
            help="💡 AI Tip: Enter a SMILES string to find similar compounds"
        )
        
        threshold = st.slider(
            "Similarity Threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            help="Higher values mean more similar compounds"
        )
        
        if st.button("🔍 Analyze Similarity"):
            if smiles_input:
                with st.spinner("🧪 Analyzing similarity..."):
                    # Create analyzer with selected options
                    analyzer = SimilarityAnalyzer(
                        radius=radius,
                        n_bits=n_bits,
                        fp_type=fp_type,
                        metric=similarity_metric
                    )
                    results = analyzer.analyze_similarity(
                        target_smiles=smiles_input,
                        heteroatom_df=st.session_state.heteroatom_results,
                        min_similarity=threshold
                    )
                    st.success("✅ Analysis complete!")
                    
                    # Show advanced molecular information
                    if len(results) > 0:
                        with st.expander("🔬 Advanced Molecular Analysis", expanded=True):
                            st.markdown("### Molecular Property Differences")
                            property_cols = [col for col in results.columns if col.startswith('Delta_')]
                            if property_cols:
                                property_df = results[['PDB_ID', 'Heteroatom_Code'] + property_cols].head(10)
                                st.dataframe(
                                    property_df,
                                    use_container_width=True,
                                    column_config={
                                        prop: st.column_config.NumberColumn(
                                            prop.replace('Delta_', 'Δ '),
                                            help="Difference from target molecule",
                                            format="%.2f"
                                        ) for prop in property_cols
                                    }
                                )
                            
                            st.markdown("### Substructure Analysis")
                            substructure_df = results[['PDB_ID', 'Heteroatom_Code', 'Has_Substructure_Match', 'Substructure_Match_Count']].head(10)
                            st.dataframe(substructure_df, use_container_width=True)
    
    else:  # Complete Pipeline
        st.subheader("Complete Pipeline Analysis")
        
        # Advanced options in pipeline mode
        with st.expander("🔬 Advanced Analysis Options", expanded=True):
            fp_type = st.selectbox(
                "Fingerprint Type",
                options=list(SimilarityAnalyzer.FINGERPRINT_TYPES.keys())
            )
            similarity_metric = st.selectbox(
                "Similarity Metric",
                options=list(SimilarityAnalyzer.SIMILARITY_METRICS.keys())
            )
        
        uniprot_input = st.text_area(
            "UniProt IDs (one per line or comma-separated)",
            help="💡 AI Tip: Enter one or more UniProt IDs to analyze"
        )
        
        smiles_input = st.text_area(
            "SMILES String",
            help="💡 AI Tip: Enter a SMILES string to find similar compounds"
        )
        
        threshold = st.slider(
            "Similarity Threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            help="Higher values mean more similar compounds"
        )
        
        if st.button("🚀 Run Complete Analysis"):
            if uniprot_input and smiles_input:
                uniprot_ids = [id.strip() for id in uniprot_input.replace(',', '\n').split('\n') if id.strip()]
                
                with st.spinner("🔄 Running complete analysis pipeline..."):
                    results = st.session_state.agent.execute_action(
                        "complete_pipeline",
                        {
                            "uniprot_ids": uniprot_ids,
                            "smiles": smiles_input,
                            "threshold": threshold,
                            "fp_type": fp_type,
                            "metric": similarity_metric
                        }
                    )
                    
                if "error" in results:
                    st.error(f"Error: {results['error']}")
                else:
                    st.success("✅ Complete analysis finished!")
                    
                    st.subheader("📊 Heteroatom Results")
                    st.write(results["heteroatom_results"])
                    
                    st.subheader("🧪 Similarity Results")
                    st.write(results["similarity_results"])

if __name__ == "__main__":
    main()